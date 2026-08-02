from collections.abc import Callable, Hashable
from typing import TypeVar

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.game_data import ItemRarity

OptionT = TypeVar("OptionT", bound=Hashable)


def rarity_summary(rarities: list[ItemRarity]) -> str:
    if not rarities:
        return "All rarities"
    return ", ".join(r.value for r in rarities)


class CheckboxListDialog[OptionT](QDialog):
    """Generic multi-select checkbox dialog with an Ok/Cancel/Clear button row.

    Subclasses (or callers) supply the option list, current selection, and labels;
    this base handles checkbox creation, layout, clearing, and selection retrieval.
    """

    def __init__(
        self,
        parent: QWidget,
        window_title: str,
        group_title: str,
        options: list[OptionT],
        selected: list[OptionT],
        note_text: str,
        option_text: Callable[[OptionT], str] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.checkboxes: dict[OptionT, QCheckBox] = {}

        selected_set = set(selected)

        layout = QVBoxLayout(self)

        group_box = QGroupBox(group_title)
        group_layout = QVBoxLayout(group_box)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for option in options:
            checkbox = QCheckBox(option_text(option) if option_text is not None else str(option))
            checkbox.setChecked(option in selected_set)
            self.checkboxes[option] = checkbox
            content_layout.addWidget(checkbox)

        scroll_area.setWidget(content_widget)
        group_layout.addWidget(scroll_area)
        layout.addWidget(group_box)

        note_label = QLabel(note_text)
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        clear_button = button_box.addButton("Clear", QDialogButtonBox.ButtonRole.ResetRole)
        if clear_button is not None:
            clear_button.clicked.connect(self.clear_selection)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def clear_selection(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected(self) -> list[OptionT]:
        return [option for option, checkbox in self.checkboxes.items() if checkbox.isChecked()]


class RarityPicker(CheckboxListDialog[ItemRarity]):
    def __init__(self, parent: QWidget, selected_rarities: list[ItemRarity]):
        super().__init__(
            parent,
            window_title="Select Rarities",
            group_title="Rarities",
            options=list(ItemRarity),
            selected=selected_rarities,
            note_text="If no rarities are selected, all rarities will be kept for this filter.",
            option_text=lambda rarity: rarity.value,
        )

    def get_selected_rarities(self) -> list[ItemRarity]:
        return self.get_selected()
