from PyQt6.QtWidgets import QCheckBox, QLineEdit, QSizePolicy, QWidget


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
