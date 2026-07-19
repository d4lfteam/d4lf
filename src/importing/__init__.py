"""Public contracts and shared behavior for build-guide importing."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

from src.importing.contracts import (
    DEFAULT_FILENAME_PARTS,
    FilenamePart,
    ImportOptions,
    ImportRequest,
    ImportResult,
    ImportSource,
    assemble_profile_file_name,
)
from src.importing.service import UnsupportedImportSourceError, import_build, select_source


def create_importer_window(parent: QWidget | None = None, accent_color: str | None = None) -> object:
    """Create the importing capability's standalone window."""
    from src.importing.gui import ImporterWindow  # ruff:ignore[import-outside-top-level]

    return ImporterWindow(parent=parent, accent_color=accent_color)


__all__ = [
    "DEFAULT_FILENAME_PARTS",
    "FilenamePart",
    "ImportOptions",
    "ImportRequest",
    "ImportResult",
    "ImportSource",
    "UnsupportedImportSourceError",
    "assemble_profile_file_name",
    "create_importer_window",
    "import_build",
    "select_source",
]
