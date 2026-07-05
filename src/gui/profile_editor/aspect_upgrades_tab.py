from src.gui.models.dialog import AddAspectUpgrade
from src.gui.models.rule_list_tab import RuleListTab

ASPECT_UPGRADES_TABNAME = "Aspect Upgrades"


class AspectUpgradesTab(RuleListTab[str]):
    def __init__(self, aspect_upgrades: list[str], parent=None):
        super().__init__(aspect_upgrades, parent)
        self.aspect_upgrades = self.items
        self.upgrade_list_widget = self.list_widget

    def description_text(self) -> str:
        return (
            "Add any legendary aspects you'd like to have favorited if an upgrade is found. "
            "See the readme on AspectUpgrades for more information."
        )

    def add_actions(self):
        return [("Add Aspect", lambda: AddAspectUpgrade(self.aspect_upgrades))]

    def on_add_accepted(self, dialog) -> str:
        aspect_upgrade = dialog.get_value()
        self.aspect_upgrades.append(aspect_upgrade)
        return aspect_upgrade

    def to_display_text(self, item: str) -> str:
        return item
