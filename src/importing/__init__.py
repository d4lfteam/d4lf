"""Public contracts and shared behavior for build-guide importing."""

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from collections.abc import Callable

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


def create_importer_window(
    parent: QWidget | None = None, on_import_completed: Callable[[], None] | None = None
) -> ImporterWindow:
    """Create the importing capability's standalone window, optionally notifying when an import completes."""
    window = ImporterWindow(parent=parent)
    if on_import_completed is not None:
        window.import_completed.connect(on_import_completed, Qt.ConnectionType.UniqueConnection)
    return window


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
