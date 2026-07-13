from typing import TYPE_CHECKING, Protocol, override, runtime_checkable

from src.gui.models.dialog import AddAspectUpgrade
from src.gui.models.rule_list_tab import RuleListTab

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QDialog

ASPECT_UPGRADES_TABNAME = "Aspect Upgrades"


@runtime_checkable
class _AspectUpgradeDialog(Protocol):
    def get_value(self) -> str: ...


class AspectUpgradesTab(RuleListTab[str]):
    def __init__(self, aspect_upgrades: list[str], parent=None):
        super().__init__(aspect_upgrades, parent)
        self.aspect_upgrades = self.items
        self.upgrade_list_widget = self.list_widget

    @override
    def description_text(self) -> str:
        return (
            "Add any legendary aspects you'd like to have favorited if an upgrade is found. "
            "See the readme on AspectUpgrades for more information."
        )

    @override
    def add_actions(self):
        return [("Add Aspect", lambda: AddAspectUpgrade(self.aspect_upgrades))]

    @override
    def on_add_accepted(self, dialog: QDialog) -> str:
        if not isinstance(dialog, _AspectUpgradeDialog):
            msg = "Aspect upgrades require an AddAspectUpgrade dialog."
            raise TypeError(msg)
        aspect_upgrade = dialog.get_value()
        self.aspect_upgrades.append(aspect_upgrade)
        return aspect_upgrade

    @override
    def to_display_text(self, item: str) -> str:
        return item
