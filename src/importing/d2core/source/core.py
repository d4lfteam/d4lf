"""Session-owned public d2core import source."""

import copy
import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from threading import Lock
from typing import cast

from src.importing.contracts import ImportRequest, ImportResult, VariantMetadata
from src.importing.d2core.browser import (
    BrowserAcquirer,
    BrowserFactory,
    BrowserSnapshot,
    NetworkObserver,
    SeleniumBrowserFactory,
    SeleniumNetworkObserver,
)
from src.importing.d2core.catalog import CatalogStore, CatalogTransport, HttpCatalogTransport, observed_catalog_version
from src.importing.d2core.diagnostics import D2CoreWarningSink
from src.importing.d2core.envelope import decode_build_envelope
from src.importing.d2core.errors import NO_USABLE_VARIANT, SCHEMA_DRIFT, D2CoreImportError
from src.importing.d2core.source.helpers import decode_body, select_variant_name
from src.importing.d2core.source.normalization import normalize_build
from src.importing.d2core.source.workflow import resolve_variants
from src.importing.d2core.url import D2CoreUrl, parse_d2core_url
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlannerSnapshot:
    """Immutable source payload plus its browser-observed catalog deployment."""

    build: Mapping[str, object]
    catalog_url: str

    @property
    def catalog_version(self) -> str:
        try:
            return observed_catalog_version(self.catalog_url)
        except ValueError as error:
            raise D2CoreImportError(SCHEMA_DRIFT, "The d2core catalog URL was invalid") from error


class D2CoreImportSource:
    """Acquire one public planner snapshot and use it for all later operations."""

    name = "d2core"

    def __init__(
        self,
        *,
        browser_factory: BrowserFactory | None = None,
        network_observer: NetworkObserver | None = None,
        catalog_transport: CatalogTransport | None = None,
        snapshot: BrowserSnapshot | PlannerSnapshot | None = None,
    ) -> None:
        self._browser_factory = browser_factory or SeleniumBrowserFactory()
        self._observer = network_observer or SeleniumNetworkObserver()
        self._catalog_transport = catalog_transport or HttpCatalogTransport()
        self._snapshot = self._as_snapshot(snapshot)
        self._catalogs: CatalogStore | None = None
        self._planner: D2CoreUrl | None = None
        self._closed = False
        self._state_lock = Lock()
        self._diagnostics = D2CoreWarningSink()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def snapshot(self) -> PlannerSnapshot | None:
        return self._snapshot

    def fetch_variants(self, request: ImportRequest) -> list[VariantMetadata]:
        try:
            _, snapshot = self._ensure_snapshot(request)
            self._ensure_open()
            variants = snapshot.build.get("variants", [])
            variant_list = cast("list[object]", variants)
            result = [
                VariantMetadata(id=str(index), name=select_variant_name(value, index))
                for index, value in enumerate(variant_list, start=1)
                if isinstance(value, Mapping)
            ]
            self._ensure_open()
        except Exception as error:
            self._log_terminal(error)
            self.close()
            raise
        else:
            return result

    def import_build(self, request: ImportRequest) -> ImportResult:
        try:
            planner, snapshot = self._ensure_snapshot(request)
            self._ensure_open()
            canonical_request = replace(request, url=planner.canonical)
            variants = snapshot.build.get("variants", [])
            selected = resolve_variants(variants, planner.variant, request, self._warn)
            self._ensure_open()
            if not selected:
                _raise_no_selection()
            build = self._build_normalized(snapshot.build, snapshot.catalog_version, selected, canonical_request)
            self._ensure_open()
            result = ImportPipeline.run_result(
                StaticBuildGuideAdapter(url=planner.canonical, build=build), canonical_request
            )
        except Exception as error:
            self._log_terminal(error)
            raise
        else:
            LOGGER.info(
                "d2core import complete: created_profiles=%d warnings=%d",
                len(result.saved_file_names),
                self._diagnostics.count,
            )
            return result
        finally:
            self.close()

    def close(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            if self._catalogs is not None:
                self._catalogs.clear()
            self._catalogs = None
            self._snapshot = None
            self._planner = None
            self._diagnostics.clear()

    def _ensure_open(self) -> None:
        with self._state_lock:
            if self._closed:
                raise D2CoreImportError(SCHEMA_DRIFT, "The d2core import session is closed")

    def _ensure_snapshot(self, request: ImportRequest) -> tuple[D2CoreUrl, PlannerSnapshot]:
        self._ensure_open()
        planner = parse_d2core_url(request.url)
        with self._state_lock:
            if self._closed:
                raise D2CoreImportError(SCHEMA_DRIFT, "The d2core import session is closed")
            if self._planner is not None and self._planner.canonical != planner.canonical:
                raise D2CoreImportError(SCHEMA_DRIFT, "A d2core session cannot change planner URLs")
            self._planner = planner
            snapshot = self._snapshot
        if snapshot is None:
            acquired = BrowserAcquirer(self._browser_factory, self._observer).acquire(planner)
            candidate = self._as_snapshot(acquired)
            with self._state_lock:
                if self._closed:
                    raise D2CoreImportError(SCHEMA_DRIFT, "The d2core import session is closed")
                self._snapshot = candidate
                snapshot = candidate
        if snapshot is None:
            raise D2CoreImportError(SCHEMA_DRIFT, "The d2core planner snapshot was missing")
        self._ensure_open()
        build = decode_build_envelope(decode_body(snapshot.build), planner.build_id)
        self._ensure_open()
        assert snapshot.catalog_version
        if build is not snapshot.build:
            replacement = PlannerSnapshot(build=copy.deepcopy(build), catalog_url=snapshot.catalog_url)
            with self._state_lock:
                if self._closed:
                    raise D2CoreImportError(SCHEMA_DRIFT, "The d2core import session is closed")
                self._snapshot = replacement
                snapshot = replacement
        return planner, snapshot

    def _build_normalized(
        self,
        raw_build: Mapping[str, object],
        version: str,
        selected: list[tuple[int, Mapping[str, object]]],
        request: ImportRequest,
    ) -> ExtractedBuild:
        catalogs = self._catalog_store(version)
        return normalize_build(
            raw_build,
            selected,
            request,
            catalogs,
            source_name=self.name,
            ensure_open=self._ensure_open,
            warn=self._warn,
            set_variant=self._diagnostics.set_variant,
        )

    def _catalog_store(self, version: str) -> CatalogStore:
        with self._state_lock:
            if self._closed:
                raise D2CoreImportError(SCHEMA_DRIFT, "The d2core import session is closed")
            if self._catalogs is None:
                self._catalogs = CatalogStore(version=version, transport=self._catalog_transport)
            return self._catalogs

    def _warn(self, code: str, variant: str, module: str, key: str) -> None:
        self._diagnostics.warn(code, variant, module, key)

    @staticmethod
    def _as_snapshot(snapshot: BrowserSnapshot | PlannerSnapshot | None) -> PlannerSnapshot | None:
        if snapshot is None:
            return None
        if isinstance(snapshot, PlannerSnapshot):
            return PlannerSnapshot(build=copy.deepcopy(snapshot.build), catalog_url=snapshot.catalog_url)
        return PlannerSnapshot(
            build=cast("Mapping[str, object]", copy.deepcopy(snapshot.response_body)), catalog_url=snapshot.catalog_url
        )

    @staticmethod
    def _log_terminal(error: Exception) -> None:
        if isinstance(error, D2CoreImportError):
            LOGGER.error("%s %s", error.code, error.detail)


def _raise_no_selection() -> None:
    raise D2CoreImportError(NO_USABLE_VARIANT, "No selected d2core Variant could be resolved")
