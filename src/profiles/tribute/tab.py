from typing import TYPE_CHECKING, cast, override

from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.game_data import GameCatalog
from src.profiles import TributeFilterModel
from src.profiles.editor.pickers import RarityPicker, rarity_summary
from src.profiles.editor.rule_list import DialogFactory, RuleListTab
from src.profiles.tribute.dialogs import CreateTribute

if TYPE_CHECKING:
    from collections.abc import Callable

TRIBUTES_TABNAME = "Tributes"
_TRIBUTE_PREFIX = "Tribute: "


class TributesTab(RuleListTab[str]):
    def __init__(self, tributes: TributeFilterModel | None, parent: QWidget | None = None) -> None:
        self.tributes = tributes if tributes is not None else TributeFilterModel()
        super().__init__(self.tributes.name, parent)
        self.rarity_line_edit = QLineEdit()

    @override
    def description_text(self) -> str:
        return "Add tribute names and select rarities you want to keep. Leaving rarities empty keeps all rarities."

    @override
    def add_actions(self) -> list[tuple[str, DialogFactory]]:
        return [("Add Tribute", lambda: CreateTribute(self.items))]

    @override
    def add_extra_controls(self, layout: QVBoxLayout) -> None:
        self.rarity_line_edit.setReadOnly(True)
        self.refresh_rarity_summary()
        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_button = QPushButton("...")
        edit_rarities_button.setMaximumWidth(40)
        edit_rarities_button.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_button)
        rarity_layout.addStretch()
        rarity_form = QFormLayout()
        rarity_form.addRow("Rarities:", rarity_layout)
        layout.addLayout(rarity_form)

    @override
    def _run_add_action(self, dialog_factory: Callable[[], QDialog]) -> None:
        dialog = cast("CreateTribute", dialog_factory())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for tribute_name in dialog.get_value().name:
            if tribute_name not in self.items:
                self.items.append(tribute_name)
                self.list_widget.addItem(self.to_display_text(tribute_name))

    @override
    def to_display_text(self, item: str) -> str:
        return f"{_TRIBUTE_PREFIX}{GameCatalog().tribute_dict.get(item, item)}"

    @override
    def empty_selection_warning_text(self) -> str:
        return "Select at least one tribute rule to remove."

    def refresh_rarity_summary(self) -> None:
        self.rarity_line_edit.setText(rarity_summary(self.tributes.rarities))

    def edit_rarities(self) -> None:
        picker = RarityPicker(self, self.tributes.rarities)
        if picker.exec() == QDialog.DialogCode.Accepted:
            self.tributes.rarities = picker.get_selected_rarities()
            self.refresh_rarity_summary()
