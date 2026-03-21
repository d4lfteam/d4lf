import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QCheckBox

from src.gui.importer.importer_config import ImportVariantOption
from src.gui.importer_window import (
    IMPORTER_LOGGER_NAMES,
    PROFILE_IMPORT_CANCELLED_MESSAGE,
    PROFILE_IMPORT_CANCELLED_NO_VARIANT_SELECTED_MESSAGE,
    _build_variant_detection_log_message,
    _get_importer_source_name,
    _VariantSelectionDialog,
)


def test_importer_window_includes_gui_common_logger():
    assert "src.gui.importer_window" in IMPORTER_LOGGER_NAMES
    assert "src.gui.importer.gui_common" in IMPORTER_LOGGER_NAMES
    assert "src.gui.importer.common" not in IMPORTER_LOGGER_NAMES


def test_variant_detection_log_message_explain_why_no_dialog_opens():
    message = _build_variant_detection_log_message(
        url="https://d4builds.gg/builds/example/?var=0",
        variant_options=[ImportVariantOption(id="0", label="Uber (P230)")],
    )

    assert message == "Discovered 1 D4Builds variant."


def test_get_importer_source_name_returns_user_facing_labels():
    assert _get_importer_source_name("https://d4builds.gg/builds/example") == "D4Builds"
    assert _get_importer_source_name("https://maxroll.gg/d4/build-guides/example") == "Maxroll"
    assert _get_importer_source_name("https://mobalytics.gg/diablo-4/builds/example") == "Mobalytics"


def test_profile_import_cancelled_message_matches_ui_copy():
    assert PROFILE_IMPORT_CANCELLED_MESSAGE == "Profile import cancelled"


def test_profile_import_cancelled_no_variant_selected_message_matches_ui_copy():
    assert PROFILE_IMPORT_CANCELLED_NO_VARIANT_SELECTED_MESSAGE == "Profile import cancelled, no variant selected"


def test_variant_selection_dialog_uses_importer_checkbox_widgets():
    _ = QApplication.instance() or QApplication([])
    dialog = _VariantSelectionDialog(
        [
            ImportVariantOption(id="0", label="Starter"),
            ImportVariantOption(id="1", label="Pit Push"),
        ]
    )

    try:
        first_item = dialog.variant_list.item(0)
        first_checkbox = dialog.variant_list.itemWidget(first_item)

        assert isinstance(first_checkbox, QCheckBox)
        assert dialog.selected_variant_ids() == ("0", "1")

        dialog._set_all_checked(Qt.CheckState.Unchecked)

        assert dialog.selected_variant_ids() == ()
    finally:
        dialog.close()
