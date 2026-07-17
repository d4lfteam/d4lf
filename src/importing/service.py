"""Application-facing source selection for build-guide imports.

Source modules remain extraction adapters.  This module owns the small amount of
composition needed to select one and translate the normalized request into the
adapter's internal options, including its retry and browser behavior.
"""

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

from src.importing.contracts import ImportRequest, ImportResult, ImportSource


class UnsupportedImportSourceError(ValueError):
    """Raised when a URL does not belong to a supported build-guide source."""


Importer = Callable[..., ImportResult | None]


@dataclass(frozen=True, slots=True)
class _SelectedSource:
    name: str
    importer: Importer

    def import_build(self, request: ImportRequest) -> ImportResult:
        from src.gui.importer.importer_config import ImportConfig  # ruff:ignore[import-outside-top-level]

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
        from src.gui.importer.maxroll import import_maxroll  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("maxroll", import_maxroll)
    if host == "d4builds.gg" or host.endswith(".d4builds.gg"):
        from src.gui.importer.d4builds import import_d4builds  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("d4builds", import_d4builds)
    if host == "infinitybuilds.gg" or host.endswith(".infinitybuilds.gg"):
        from src.gui.importer.infinitybuilds import import_infinitybuilds  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("infinitybuilds", import_infinitybuilds)
    if host == "mobalytics.gg" or host.endswith(".mobalytics.gg"):
        from src.gui.importer.mobalytics import import_mobalytics  # ruff:ignore[import-outside-top-level]

        return _SelectedSource("mobalytics", import_mobalytics)
    message = f"Unsupported build-guide URL: {url}"
    raise UnsupportedImportSourceError(message)


def import_build(request: ImportRequest, source: ImportSource | None = None) -> ImportResult:
    """Import a build through one source-independent request/result seam."""
    return (source or select_source(request.url)).import_build(request)
