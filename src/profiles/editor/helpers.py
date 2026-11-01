from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QPushButton, QSizePolicy, QWidget

if TYPE_CHECKING:
    from collections.abc import Callable


def create_readonly_line_edit() -> QLineEdit:
    line_edit = QLineEdit()
    line_edit.setReadOnly(True)
    line_edit.setMinimumWidth(360)
    line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return line_edit


def create_auto_sync_checkbox() -> QCheckBox:
    checkbox = QCheckBox("Auto Sync")
    checkbox.setToolTip(
        "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
        "When unchecked: You can manually set Min Greater Affixes to any value"
    )
    return checkbox


def refresh_widget_style(widget: QWidget) -> None:
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)


def create_picker_row(line_edit: QLineEdit, on_edit: Callable[[], None]) -> QHBoxLayout:
    """Lay out a read-only summary line edit with a "..." button that opens its picker."""
    layout = QHBoxLayout()
    layout.addWidget(line_edit)
    edit_button = QPushButton("...")
    edit_button.setMaximumWidth(40)
    edit_button.clicked.connect(on_edit)
    layout.addWidget(edit_button)
    layout.addStretch()
    return layout
