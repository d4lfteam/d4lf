"""Small filename selector builder used by the importer window."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QVBoxLayout

from src.importing.contracts import DEFAULT_FILENAME_PARTS
from src.importing.gui.constants import FILENAME_PART_LABELS


def build_filename_row(window, layout: QVBoxLayout) -> None:
    row = QHBoxLayout()
    row.addWidget(QLabel("Custom file name:"))
    window.filename_input_box = QLineEdit()
    window.filename_input_box.setPlaceholderText("Leave blank for default filename")
    window.filename_input_box.textChanged.connect(window._update_generate_button_state)
    row.addWidget(window.filename_input_box)
    window.filename_parts_button = QPushButton("Default filename includes...")
    window.filename_parts_menu = QMenu(window.filename_parts_button)
    menu = window.filename_parts_menu
    window.filename_part_actions = {part: QAction(FILENAME_PART_LABELS[part], menu) for part in DEFAULT_FILENAME_PARTS}
    for part, action in window.filename_part_actions.items():
        action.setCheckable(True)
        action.setChecked(window._filename_part_setting(part))
        action.toggled.connect(lambda checked, part=part: window._handle_filename_part_toggled(part, checked))
        menu.addAction(action)
    window.filename_parts_button.setMenu(menu)
    row.addWidget(window.filename_parts_button)
    layout.addLayout(row)
    window.filename_parts_summary_label = QLabel()
    layout.addWidget(window.filename_parts_summary_label)
    window._update_filename_parts_summary()
    window._update_generate_button_state()
