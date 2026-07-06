from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTabWidget

from src.config.profile_models import TributeFilterModel
from src.gui.profile_editor.affixes_tab import AFFIXES_TABNAME, AffixesTab
from src.gui.profile_editor.aspect_upgrades_tab import ASPECT_UPGRADES_TABNAME, AspectUpgradesTab
from src.gui.profile_editor.charms_seals_group_tab import CHARMS_TABNAME, SEALS_TABNAME, CharmsTab, SealsTab
from src.gui.profile_editor.global_uniques_tab import UNIQUES_TABNAME, UniquesTab
from src.gui.profile_editor.sigils_tab import SIGILS_TABNAME, SigilsTab
from src.gui.profile_editor.tributes_tab import TRIBUTES_TABNAME, TributesTab

if TYPE_CHECKING:
    from src.config.profile_document import LoadedProfile
    from src.config.profile_models import ProfileModel


class ProfileEditor(QTabWidget):
    def __init__(self, loaded_profile: LoadedProfile, parent=None):
        super().__init__(parent)

        self.loaded_profile = loaded_profile
        self.profile_model = loaded_profile.profile
        if self.profile_model.tributes is None:
            self.profile_model.tributes = TributeFilterModel()
        elif isinstance(self.profile_model.tributes, list):
            self.profile_model.tributes = (
                self.profile_model.tributes[0] if self.profile_model.tributes else TributeFilterModel()
            )
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
