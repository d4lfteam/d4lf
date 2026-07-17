"""Application-facing source selection for build-guide imports.

Source modules remain extraction adapters.  This module owns the small amount of
composition needed to select one and translate the normalized request into the
adapter's internal options, including its retry and browser behavior.
"""

from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from src.importing.contracts import ImportRequest, ImportResult, ImportSource


class UnsupportedImportSourceError(ValueError):
    """Raised when a URL does not belong to a supported build-guide source."""


class _SelectedSource:
    def __init__(self, name: str, importer, *, normalized_request: bool = True) -> None:
        self.name = name
        self.importer = importer
        self.normalized_request = normalized_request

    def import_build(self, request: ImportRequest) -> ImportResult:
        if self.normalized_request:
            result = self.importer(request)
        else:
            from src.importing.config import ImportConfig  # ruff:ignore[import-outside-top-level]

            options = request.options
            result = self.importer(
                config=ImportConfig(
                    url=request.url,
                    import_aspect_upgrades=options.import_aspect_upgrades,
                    add_to_profiles=options.add_to_profiles,
                    import_greater_affixes=options.import_greater_affixes,
                    require_greater_affixes=options.require_greater_affixes,
                    export_paragon=options.export_paragon,
                    custom_file_name=options.custom_file_name,
                    filename_parts=options.filename_parts,
                )
            )
        if result is None:
            message = f"The {self.name} importer did not produce a result"
            raise RuntimeError(message)
        return result


def select_source(url: str) -> ImportSource:
    """Select the source adapter for a normalized build-guide URL."""
    host = (urlparse(url.strip()).hostname or "").casefold()
    if host == "maxroll.gg" or host.endswith(".maxroll.gg"):
        from src.importing.maxroll import import_maxroll  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("maxroll", import_maxroll)
    if host == "d4builds.gg" or host.endswith(".d4builds.gg"):
        from src.importing.d4builds import import_d4builds  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("d4builds", import_d4builds)
    if host == "infinitybuilds.gg" or host.endswith(".infinitybuilds.gg"):
        from src.importing.infinitybuilds import import_infinitybuilds  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("infinitybuilds", import_infinitybuilds)
    if host == "mobalytics.gg" or host.endswith(".mobalytics.gg"):
        from src.importing.mobalytics import import_mobalytics  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("mobalytics", import_mobalytics)
    message = f"Unsupported build-guide URL: {url}"
    raise UnsupportedImportSourceError(message)


def import_build(request: ImportRequest, source: ImportSource | None = None) -> ImportResult:
    """Import a build through one source-independent request/result seam."""
    return (source or select_source(request.url)).import_build(request)
