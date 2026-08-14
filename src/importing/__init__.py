"""Public contracts and shared behavior for build-guide importing."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

from src.importing.contracts import (
    DEFAULT_FILENAME_PARTS,
    FilenamePart,
    ImportOptions,
    ImportRequest,
    ImportResult,
    ImportSession,
    ImportSource,
    ImportSourceError,
    VariantMetadata,
    VariantSelection,
    assemble_profile_file_name,
)
from src.importing.gui import ImporterWindow
from src.importing.service import UnsupportedImportSourceError, import_build, open_session, select_source


def create_importer_window(parent: QWidget | None = None, accent_color: str | None = None) -> ImporterWindow:
    """Create the importing capability's standalone window."""
    return ImporterWindow(parent=parent, accent_color=accent_color)


__all__ = [
    "DEFAULT_FILENAME_PARTS",
    "FilenamePart",
    "ImportOptions",
    "ImportRequest",
    "ImportResult",
    "ImportSession",
    "ImportSource",
    "ImportSourceError",
    "UnsupportedImportSourceError",
    "VariantMetadata",
    "VariantSelection",
    "assemble_profile_file_name",
    "create_importer_window",
    "import_build",
    "open_session",
    "select_source",
]
