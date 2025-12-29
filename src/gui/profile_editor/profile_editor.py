import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTabWidget

from src.config.models import ProfileModel
from src.gui.importer.common import save_as_profile
from src.gui.profile_editor.affixes_tab import AFFIXES_TABNAME, AffixesTab
from src.gui.profile_editor.aspect_upgrades_tab import ASPECT_UPGRADES_TABNAME, AspectUpgradesTab
from src.gui.profile_editor.sigils_tab import SIGILS_TABNAME, SigilsTab
from src.gui.profile_editor.tributes_tab import TRIBUTES_TABNAME, TributesTab
from src.gui.profile_editor.uniques_tab import UNIQUES_TABNAME, UniquesTab

LOGGER = logging.getLogger(__name__)


class ProfileEditor(QTabWidget):
    def __init__(self, profile_model: ProfileModel, parent=None):
        super().__init__(parent)
        self.profile_model = profile_model
        # Create main tabs
        self.affixes_tab = AffixesTab(self.profile_model.Affixes)
        self.aspect_upgrades_tab = AspectUpgradesTab(self.profile_model.AspectUpgrades)
        self.sigils_tab = SigilsTab(self.profile_model.Sigils)
        self.tributes_tab = TributesTab(self.profile_model.Tributes)
        self.uniques_tab = UniquesTab(self.profile_model.Uniques)

        self.currentChanged.connect(self.tab_changed)
        # Add tabs with icons
        self.addTab(self.affixes_tab, AFFIXES_TABNAME)
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
        """Save all tabs' configurations"""
        # Manually sync minGreaterAffixCount before saving
        for affix_filter in self.profile_model.Affixes:
            for item_name, item_filter in affix_filter.root.items():
                want_greater_count = 0
                for pool in item_filter.affixPool:
                    for affix in pool.count:
                        if getattr(affix, 'want_greater', False):
                            want_greater_count += 1

                # If checkboxes are used, use checkbox count
                if want_greater_count > 0:
                    item_filter.minGreaterAffixCount = want_greater_count
                else:
                    # No checkboxes - need to read the current UI spinner value
                    # Find the corresponding tab
                    for i in range(self.affixes_tab.tab_widget.count()):
                        tab = self.affixes_tab.tab_widget.widget(i)
                        if tab.item_name == item_name:
                            item_filter.minGreaterAffixCount = tab.min_greater.value()
                            break

        # Same for Uniques
        for unique in self.profile_model.Uniques:
            want_greater_count = sum(1 for affix in unique.affix if getattr(affix, 'want_greater', False))
            if want_greater_count > 0:
                unique.minGreaterAffixCount = want_greater_count
            # For uniques, we'd need to access the uniques tab UI similarly if needed

        try:
            # Validate
            model = ProfileModel.model_validate(self.profile_model)
            if model != self.profile_model:
                if self.show_warning():
                    save_as_profile(
                        self.profile_model.name, self.profile_model, "custom", exclude={"name"}, backup_file=True
                    )
                    QMessageBox.information(
                        self, "Info", f"Profile saved successfully to {self.profile_model.name + '.yaml'}"
                    )
                else:
                    QMessageBox.information(self, "Info", "Profile not saved.")
            else:
                save_as_profile(self.profile_model.name, self.profile_model, "custom", exclude={"name"},
                                backup_file=True)
                QMessageBox.information(self, "Info",
                                        f"Profile saved successfully to {self.profile_model.name + '.yaml'}")
        except Exception as e:
            LOGGER.error(f"Validation error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")