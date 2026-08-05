import os
from typing import TYPE_CHECKING, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QMenu, QPushButton, QVBoxLayout, QWidget

from src.importing.contracts import DEFAULT_FILENAME_PARTS, FilenamePart
from src.importing.gui.constants import FILENAME_PART_LABELS
from src.importing.gui.filename_parts import build_filename_row

if TYPE_CHECKING:
    from PyQt6.QtGui import QAction


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return cast("QApplication", QApplication.instance() or QApplication([]))


class _FilenameWindow:
    filename_input_box: QLineEdit
    filename_parts_button: QPushButton
    filename_parts_menu: QMenu
    filename_part_actions: dict[FilenamePart, QAction]
    filename_parts_summary_label: QLabel

    def __init__(self) -> None:
        self.settings = {FilenamePart.CLASS: False}
        self.toggles: list[tuple[FilenamePart, bool]] = []
        self.summary_updates = 0
        self.generate_button_updates = 0

    def _filename_part_setting(self, part: FilenamePart) -> bool:
        return self.settings.get(part, True)

    def _handle_filename_part_toggled(self, part: FilenamePart, checked: bool) -> None:
        self.toggles.append((part, checked))
        self._update_filename_parts_summary()
        self._update_generate_button_state()

    def _update_filename_parts_summary(self) -> None:
        self.summary_updates += 1
        labels = [FILENAME_PART_LABELS[part] for part in self._selected_filename_parts()]
        suffix = "_".join(labels) + ".yaml" if labels else "none"
        self.filename_parts_summary_label.setText(f"Default file name: {suffix}")

    def _selected_filename_parts(self) -> tuple[FilenamePart, ...]:
        return tuple(part for part in DEFAULT_FILENAME_PARTS if self.filename_part_actions[part].isChecked())

    def _update_generate_button_state(self) -> None:
        self.generate_button_updates += 1


def test_build_filename_row_creates_controls_and_wires_callbacks(qapp: QApplication) -> None:
    del qapp
    window = _FilenameWindow()
    container = QWidget()
    layout = QVBoxLayout(container)

    build_filename_row(window, layout)

    assert layout.count() == 2
    assert window.filename_input_box.placeholderText() == "Leave blank for default filename"
    assert window.filename_parts_button.menu() is window.filename_parts_menu
    assert [action.text() for action in window.filename_part_actions.values()] == [
        FILENAME_PART_LABELS[part] for part in DEFAULT_FILENAME_PARTS
    ]
    assert all(action.isCheckable() for action in window.filename_part_actions.values())
    assert not window.filename_part_actions[FilenamePart.CLASS].isChecked()
    assert window.filename_parts_summary_label.text() == "Default file name: Source_Season_Build title_Variant.yaml"
    assert window.summary_updates == 1
    assert window.generate_button_updates == 1

    window.filename_input_box.setText("custom")
    window.filename_part_actions[FilenamePart.CLASS].setChecked(True)

    assert window.generate_button_updates == 3
    assert window.toggles == [(FilenamePart.CLASS, True)]
    assert (
        window.filename_parts_summary_label.text() == "Default file name: Source_Season_Class_Build title_Variant.yaml"
    )

    container.close()
