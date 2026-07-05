from typing import TypeVar

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ItemType = TypeVar("ItemType")


class RuleListTab[ItemType](QWidget):
    def __init__(self, items: list[ItemType] | None, parent=None):
        super().__init__(parent)
        self.items = items if items is not None else []
        self.list_widget = QListWidget()
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 20, 0, 20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel(self.description_text())
        label.setWordWrap(True)
        main_layout.addWidget(label)

        button_layout = QHBoxLayout()
        for button_label, dialog_factory in self.add_actions():
            add_button = QPushButton(button_label)
            add_button.clicked.connect(
                lambda _checked=False, action_dialog_factory=dialog_factory: self._run_add_action(action_dialog_factory)
            )
            button_layout.addWidget(add_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(remove_button)
        main_layout.addLayout(button_layout)

        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._reload_list_widget()
        main_layout.addWidget(self.list_widget)
        self.setLayout(main_layout)

    def _reload_list_widget(self):
        self.list_widget.clear()
        for item in self.items:
            self.list_widget.addItem(self.to_display_text(item))

    def _run_add_action(self, dialog_factory):
        dialog = dialog_factory()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = self.on_add_accepted(dialog)
            self.list_widget.addItem(self.to_display_text(item))

    def remove_selected(self):
        rows = sorted({self.list_widget.row(item) for item in self.list_widget.selectedItems()}, reverse=True)
        if not rows:
            QMessageBox.warning(self, "Warning", self.empty_selection_warning_text())
            return

        for row in rows:
            self.list_widget.takeItem(row)
            self.items.pop(row)

    def description_text(self) -> str:
        msg = "Subclasses must implement description_text()."
        raise NotImplementedError(msg)

    def add_actions(self):
        msg = "Subclasses must implement add_actions()."
        raise NotImplementedError(msg)

    def on_add_accepted(self, dialog: QDialog) -> ItemType:
        msg = "Subclasses must implement on_add_accepted()."
        raise NotImplementedError(msg)

    def to_display_text(self, item: ItemType) -> str:
        msg = "Subclasses must implement to_display_text()."
        raise NotImplementedError(msg)

    def empty_selection_warning_text(self) -> str:
        return "Select at least one rule to remove."
