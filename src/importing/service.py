"""Application-facing source selection for build-guide imports.

Source modules remain extraction adapters.  This module owns the small amount of
composition needed to select one and translate the normalized request into the
adapter's internal options, including its retry and browser behavior.
"""

from collections.abc import Callable
from urllib.parse import urlparse

from src.importing.contracts import ImportRequest, ImportResult, ImportSource, VariantMetadata

ImportCallable = Callable[[ImportRequest], ImportResult | None]
VariantFetcher = Callable[[ImportRequest], list[VariantMetadata]]


class UnsupportedImportSourceError(ValueError):
    """Raised when a URL does not belong to a supported build-guide source."""


class _SelectedSource:
    def __init__(self, name: str, importer: ImportCallable, fetcher: VariantFetcher) -> None:
        self.name = name
        self.importer = importer
        self.fetcher = fetcher

    def fetch_variants(self, request: ImportRequest) -> list[VariantMetadata]:
        return self.fetcher(request)

    def import_build(self, request: ImportRequest) -> ImportResult:
        result = self.importer(request)
        if result is None:
            message = f"The {self.name} importer did not produce a result"
            raise RuntimeError(message)
        return result


def select_source(url: str) -> ImportSource:
    """Select the source adapter for a normalized build-guide URL."""
    host = (urlparse(url.strip()).hostname or "").casefold()
    if host == "maxroll.gg" or host.endswith(".maxroll.gg"):
        from src.importing.maxroll import (  # ruff:ignore[import-outside-top-level]
            fetch_variants_maxroll,
            import_maxroll,
        )

        return _SelectedSource("maxroll", import_maxroll, fetch_variants_maxroll)
    if host == "d4builds.gg" or host.endswith(".d4builds.gg"):
        from src.importing.d4builds import (  # ruff:ignore[import-outside-top-level]
            fetch_variants_d4builds,
            import_d4builds,
        )

        return _SelectedSource("d4builds", import_d4builds, fetch_variants_d4builds)
    if host == "infinitybuilds.gg" or host.endswith(".infinitybuilds.gg"):
        from src.importing.infinitybuilds import (  # ruff:ignore[import-outside-top-level]
            fetch_variants_infinitybuilds,
            import_infinitybuilds,
        )

        return _SelectedSource("infinitybuilds", import_infinitybuilds, fetch_variants_infinitybuilds)
    if host == "mobalytics.gg" or host.endswith(".mobalytics.gg"):
        from src.importing.mobalytics import (  # ruff:ignore[import-outside-top-level]
            fetch_variants_mobalytics,
            import_mobalytics,
        )

        return _SelectedSource("mobalytics", import_mobalytics, fetch_variants_mobalytics)
    message = f"Unsupported build-guide URL: {url}"
    raise UnsupportedImportSourceError(message)


def import_build(request: ImportRequest, source: ImportSource | None = None) -> ImportResult:
    """Import a build through one source-independent request/result seam."""
    return (source or select_source(request.url)).import_build(request)
