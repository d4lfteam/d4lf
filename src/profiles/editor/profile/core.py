from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget

from src.profiles import TributeFilterModel
from src.profiles.affix import AFFIXES_TABNAME, AffixesTab
from src.profiles.aspect import ASPECT_UPGRADES_TABNAME, AspectUpgradesTab
from src.profiles.charm_seal import CHARMS_TABNAME, SEALS_TABNAME, CharmsTab, SealsTab
from src.profiles.sigil import SIGILS_TABNAME, SigilsTab
from src.profiles.tribute import TRIBUTES_TABNAME, TributesTab
from src.profiles.unique import UNIQUES_TABNAME, UniquesTab

if TYPE_CHECKING:
    from src.profiles import LoadedProfile, ProfileModel


def _to_editor_tribute_filter(tributes: TributeFilterModel | None) -> TributeFilterModel:
    return tributes if tributes is not None else TributeFilterModel()


class ProfileEditor(QTabWidget):
    def __init__(self, loaded_profile: LoadedProfile, parent=None):
        super().__init__(parent)

        self.loaded_profile = loaded_profile
        self.profile_model = loaded_profile.profile
        self.profile_model.tributes = _to_editor_tribute_filter(self.profile_model.tributes)
        # Create main tabs
        self.affixes_tab = AffixesTab(self.profile_model.affixes)
        self.charms_tab = CharmsTab(self.profile_model.charms)
        self.seals_tab = SealsTab(self.profile_model.seals)
        self.aspect_upgrades_tab = AspectUpgradesTab(self.profile_model.aspect_upgrades)
        self.sigils_tab = SigilsTab(self.profile_model.sigils)
        self.tributes_tab = TributesTab(self.profile_model.tributes)
        self.uniques_tab = UniquesTab(self.profile_model.global_uniques)

        self.currentChanged.connect(self.tab_changed)
        # Add tabs with icons
        self.addTab(self.affixes_tab, AFFIXES_TABNAME)
        self.addTab(self.charms_tab, CHARMS_TABNAME)
        self.addTab(self.seals_tab, SEALS_TABNAME)
        self.addTab(self.aspect_upgrades_tab, ASPECT_UPGRADES_TABNAME)
        self.addTab(self.sigils_tab, SIGILS_TABNAME)
        self.addTab(self.tributes_tab, TRIBUTES_TABNAME)
        self.addTab(self.uniques_tab, UNIQUES_TABNAME)

        # Configure tab widget properties
        self.setDocumentMode(True)
        self.setMovable(False)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setElideMode(Qt.TextElideMode.ElideRight)

    def tab_changed(self, index):
        if self.tabText(index) == AFFIXES_TABNAME:
            self.affixes_tab.load()
        elif self.tabText(index) == CHARMS_TABNAME:
            self.charms_tab.load()
        elif self.tabText(index) == SEALS_TABNAME:
            self.seals_tab.load()
        elif self.tabText(index) == ASPECT_UPGRADES_TABNAME:
            self.aspect_upgrades_tab.load()
        elif self.tabText(index) == SIGILS_TABNAME:
            self.sigils_tab.load()
        elif self.tabText(index) == TRIBUTES_TABNAME:
            self.tributes_tab.load()
        elif self.tabText(index) == UNIQUES_TABNAME:
            self.uniques_tab.load()

    def get_current_model(self) -> ProfileModel:
        return self.profile_model
