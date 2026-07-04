from src.config.profile_models import ItemRarity, TributeFilterModel
from src.dataloader import Dataloader
from src.gui.models.dialog import AddTributeRarity, CreateTribute
from src.gui.models.rule_list_tab import RuleListTab

TRIBUTES_TABNAME = "Tributes"


class TributesTab(RuleListTab[TributeFilterModel]):
    def __init__(self, tributes: list[TributeFilterModel] | None, parent=None):
        super().__init__(tributes, parent)
        self.tributes = self.items
        self.tribute_list_widget = self.list_widget

    def description_text(self) -> str:
        return "Add tribute names and tribute rarities you want to keep. These rules are evaluated independently."

    def to_display_text(self, tribute: TributeFilterModel) -> str:
        if not tribute.name and not tribute.rarities:
            return "Empty tribute rule"

        parts = []
        if tribute.name:
            tribute_name = Dataloader().tribute_dict.get(tribute.name, tribute.name)
            parts.append(f"Tribute: {tribute_name}")

        if tribute.rarities:
            rarity_names = ", ".join(ItemRarity(rarity).name for rarity in tribute.rarities)
            parts.append(f"Rarities: {rarity_names}")

        return " | ".join(parts)

    def add_actions(self):
        return [
            ("Add Tribute", lambda: CreateTribute(self._existing_tribute_names())),
            ("Add Rarity", lambda: AddTributeRarity(self._existing_rarities())),
        ]

    def on_add_accepted(self, dialog) -> TributeFilterModel:
        tribute_filter = dialog.get_value()
        self.tributes.append(tribute_filter)
        return tribute_filter

    def empty_selection_warning_text(self) -> str:
        return "Select at least one tribute rule to remove."

    def _existing_tribute_names(self) -> list[str]:
        return [tribute.name for tribute in self.tributes if tribute.name and not tribute.rarities]

    def _existing_rarities(self) -> list[ItemRarity]:
        return [
            ItemRarity(tribute.rarities[0])
            for tribute in self.tributes
            if tribute.rarities and not tribute.name and len(tribute.rarities) == 1
        ]
