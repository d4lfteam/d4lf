import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QTabWidget

from src.config.profile_document import LoadedProfile, ProfileDocumentStore
from src.config.profile_models import ProfileModel
from src.gui.profile_editor.affixes_tab import AFFIXES_TABNAME, AffixesTab
from src.gui.profile_editor.aspect_upgrades_tab import ASPECT_UPGRADES_TABNAME, AspectUpgradesTab
from src.gui.profile_editor.charms_tab import CHARMS_TABNAME, CharmsTab
from src.gui.profile_editor.global_uniques_tab import UNIQUES_TABNAME, UniquesTab
from src.gui.profile_editor.seals_tab import SEALS_TABNAME, SealsTab
from src.gui.profile_editor.sigils_tab import SIGILS_TABNAME, SigilsTab
from src.gui.profile_editor.tributes_tab import TRIBUTES_TABNAME, TributesTab

LOGGER = logging.getLogger(__name__)


class ProfileEditor(QTabWidget):
    # Signal emitted when profile is saved (passes profile name)
    profile_saved = pyqtSignal(str)

    def __init__(self, loaded_profile: LoadedProfile, parent=None):
        super().__init__(parent)

        self.loaded_profile = loaded_profile
        self.profile_model = loaded_profile.profile
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

    @staticmethod
    def show_warning():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Warning")

        # Newline in message text
        msg.setText("The profile model might not be valid. Do you still want to save your changes ?")

        msg.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard)

        response = msg.exec()
        return response == QMessageBox.StandardButton.Save

    def save_all(self):
        """Save all tabs' configurations."""
        try:
            # Validate
            model = ProfileModel.model_validate(self.profile_model)
            if model != self.profile_model:
                if self.show_warning():
                    saved = ProfileDocumentStore.default().save_existing(
                        loaded=self.loaded_profile, profile=self.profile_model, source="custom", backup_original=True
                    )
                    # Emit signal for hot reload
                    self.profile_saved.emit(self.profile_model.name)
                    QMessageBox.information(self, "Info", f"Profile saved successfully to {saved.path.name}")
                else:
                    QMessageBox.information(self, "Info", "Profile not saved.")
            else:
                saved = ProfileDocumentStore.default().save_existing(
                    loaded=self.loaded_profile, profile=self.profile_model, source="custom", backup_original=True
                )
                # Emit signal for hot reload
                self.profile_saved.emit(self.profile_model.name)
                QMessageBox.information(self, "Info", f"Profile saved successfully to {saved.path.name}")
        except Exception as e:
            LOGGER.exception("Failed to save profile")
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")
