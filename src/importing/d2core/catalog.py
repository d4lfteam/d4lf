"""Versioned English catalog transport and shape validation."""

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import cast, override
from urllib.parse import urlsplit

import httpx

from src.importing.d2core.errors import EQUIPMENT_CATALOG, D2CoreCatalogError
from src.perception import clean_str, correct_name

LOGGER = logging.getLogger(__name__)
CATALOG_HOST = "cloudstorage.d2core.com"
COLLECTIONS = {
    "affix": ("affix",),
    "uniqueItem": (),
    "aspect": (),
    "talisman": ("charm", "seal", "itemSets", "affixes"),
    "paragon": (),
}
AFFIX_COLLECTION_MISSING = "affix collection missing"
TALISMAN_COLLECTIONS_MISSING = "talisman collections missing"
TALISMAN_AFFIX_COLLECTIONS_MISSING = "talisman affix collections missing"
PARAGON_COLLECTIONS_MISSING = "paragon collections missing"
UNSUPPORTED_CATALOG = "unsupported catalog"
CATALOG_COLLECTION_MISSING = "catalog collection must be a list or object"
CATALOG_RECORD_MISSING_KEY = "catalog record missing stable key"
CATALOG_URL_INVALID = "catalog URL is not a versioned English d2core catalog"
CATALOG_VERSION_MISSING = "catalog version missing"


class CatalogTransport:
    def get(self, url: str, *, timeout: float) -> object:  # pragma: no cover - protocol-shaped base
        raise NotImplementedError


class HttpCatalogTransport(CatalogTransport):
    @override
    def get(self, url: str, *, timeout: float) -> object:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()


@dataclass(slots=True)
class CatalogStore:
    version: str
    transport: CatalogTransport
    sleeper: Callable[[float], None] = time.sleep
    attempts: int = 3
    timeout: float = 10.0
    data: dict[str, dict[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.attempts = min(max(self.attempts, 1), 3)
        self.timeout = min(max(self.timeout, 0.01), 10.0)

    def require(self, kind: str) -> dict[str, object]:
        return self._load(kind)

    def optional(self, kind: str) -> dict[str, object]:
        return self._load(kind)

    def clear(self) -> None:
        self.data.clear()

    def _load(self, kind: str) -> dict[str, object]:
        if kind in self.data:
            return self.data[kind]
        if kind not in COLLECTIONS:
            raise D2CoreCatalogError(EQUIPMENT_CATALOG, "Unknown d2core catalog kind")
        url = catalog_url(self.version, kind)
        last_error: Exception | None = None
        for attempt in range(self.attempts):
            try:
                raw = self._get(url)
                checked = validate_catalog(kind, raw)
            except (httpx.HTTPError, OSError, TimeoutError, ValueError) as error:
                last_error = error
                if attempt + 1 < self.attempts and _retryable(error):
                    self.sleeper(0.05 * (2**attempt))
                elif not _retryable(error):
                    break
            else:
                self.data[kind] = checked
                return checked
        detail = f"Unable to fetch the d2core {kind} catalog"
        raise D2CoreCatalogError(EQUIPMENT_CATALOG, detail, context={"catalog": kind}) from last_error

    def _get(self, url: str) -> object:
        return self.transport.get(url, timeout=self.timeout)


def catalog_url(version: str, kind: str) -> str:
    return f"https://{CATALOG_HOST}/data/d4/{version}/{kind}_enUS.json?env=prod&v=8"


def validate_catalog(kind: str, value: object) -> dict[str, object]:
    if kind == "affix":
        if not isinstance(value, Mapping) or not isinstance(value.get("affix"), list):
            raise ValueError(AFFIX_COLLECTION_MISSING)
        source = cast("Mapping[str, object]", value)
        return {kind: _index_records(source["affix"])}
    if kind == "talisman":
        if not isinstance(value, Mapping) or any(
            not isinstance(value.get(key), (dict, list)) for key in COLLECTIONS[kind]
        ):
            raise ValueError(TALISMAN_COLLECTIONS_MISSING)
        source = cast("Mapping[str, object]", value)
        indexed: dict[str, object] = {key: _index_records(source[key]) for key in COLLECTIONS[kind] if key != "affixes"}
        affixes = source["affixes"]
        if not isinstance(affixes, Mapping):
            raise ValueError(TALISMAN_AFFIX_COLLECTIONS_MISSING)
        indexed["affixes"] = {str(category): _index_records(records) for category, records in affixes.items()}
        return indexed
    if kind in {"uniqueItem", "aspect"}:
        if not isinstance(value, (Mapping, list)):
            message = f"{kind} collection missing"
            raise ValueError(message)
        return {kind: _index_records(value)}
    if kind == "paragon":
        if not isinstance(value, Mapping) or not any(_valid_paragon_class(item) for item in value.values()):
            raise ValueError(PARAGON_COLLECTIONS_MISSING)
        source = cast("Mapping[object, object]", value)
        return {str(key): item for key, item in source.items()}
    raise ValueError(UNSUPPORTED_CATALOG)


def _index_records(records: object) -> dict[str, object]:
    if isinstance(records, Mapping):
        source = cast("Mapping[object, object]", records)
        return {str(key): value for key, value in source.items()}
    if not isinstance(records, list):
        raise ValueError(CATALOG_COLLECTION_MISSING)
    result: dict[str, object] = {}
    for record in records:
        if not isinstance(record, Mapping) or not record.get("key"):
            raise ValueError(CATALOG_RECORD_MISSING_KEY)
        source = cast("Mapping[object, object]", record)
        result[str(source["key"])] = {str(key): value for key, value in source.items()}
    return result


def observed_catalog_version(catalog_url_value: str) -> str:
    parts = urlsplit(catalog_url_value)
    segments = parts.path.split("/")
    if (
        parts.scheme.casefold() != "https"
        or parts.hostname != CATALOG_HOST
        or len(segments) != 5
        or segments[1:3] != ["data", "d4"]
        or not segments[3]
        or not segments[-1].casefold().endswith("_enus.json")
    ):
        raise ValueError(CATALOG_URL_INVALID)
    version = segments[-2]
    if not version:
        raise ValueError(CATALOG_VERSION_MISSING)
    return version


def canonical_catalog_name(record: Mapping[str, object] | object, mapping: Mapping[str, object]) -> str | None:
    """Match a catalog record's stable key or localized names to D4LF's canonical name."""
    if not isinstance(record, Mapping):
        return None
    for value in (record.get("key"), record.get("name"), record.get("engName")):
        normalized = correct_name(str(value or "")) or ""
        if normalized in mapping:
            return normalized
        key_match = next((key for key in mapping if correct_name(str(key)) == normalized), None)
        if key_match is not None:
            return key_match
        match = next((key for key, label in mapping.items() if correct_name(str(label)) == normalized), None)
        if match:
            return match
    return None


def canonical_affix_name(record: Mapping[str, object] | object, mapping: Mapping[str, object]) -> str | None:
    """Match a current d2core affix description to D4LF's canonical name."""
    if not isinstance(record, Mapping):
        return None
    description = record.get("desc")
    if not isinstance(description, str):
        return None
    normalized = correct_name(clean_str(description)) or ""
    if normalized in mapping:
        return normalized
    match = next((key for key, label in mapping.items() if correct_name(str(label)) == normalized), None)
    if match:
        return match
    return None


def _valid_paragon_class(value: object) -> bool:
    return isinstance(value, Mapping) and all(isinstance(value.get(key), Mapping) for key in ("board", "node", "glyph"))


def _retryable(error: Exception) -> bool:
    if isinstance(error, ValueError):
        return False
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status in {408, 429} or status >= 500
    return True
