from PyQt6.QtWidgets import (QWidget, QTabWidget, QMessageBox)
from PyQt6.QtCore import Qt
from src.config.models import ProfileModel
from src.gui.affixes_tab import AffixesTab

class SigilsTab(QWidget):
    def __init__(self, profile_model: ProfileModel, parent=None):
        super().__init__(parent)
        # Sigils-specific UI implementation
        pass

class TributesTab(QWidget):
    def __init__(self, profile_model: ProfileModel, parent=None):
        super().__init__(parent)
        # Tributes-specific UI implementation
        pass

class UniquesTab(QWidget):
    def __init__(self, profile_model: ProfileModel, parent=None):
        super().__init__(parent)
        # Uniques-specific UI implementation
        pass

class ProfileEditor(QTabWidget):
    def __init__(self, profile_model: ProfileModel, parent=None):
        super().__init__(parent)
        self.profile_model = profile_model
        self.setup_ui()

    def setup_ui(self):
        # Create main tabs
        self.affixes_tab = AffixesTab(self.profile_model)
        self.sigils_tab = SigilsTab(self.profile_model)  # To be implemented
        self.tributes_tab = TributesTab(self.profile_model)  # To be implemented
        self.uniques_tab = UniquesTab(self.profile_model)  # To be implemented

        # Add tabs with icons
        self.addTab(self.affixes_tab, "Affixes")
        self.addTab(self.sigils_tab, "Sigils")
        self.addTab(self.tributes_tab, "Tributes")
        self.uniques_index = self.addTab(self.uniques_tab, "Uniques")

        # Configure tab widget properties
        self.setDocumentMode(True)
        self.setMovable(False)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setElideMode(Qt.TextElideMode.ElideRight)

        # Connect signals
        self.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """Handle tab changes and validation"""
        if index == self.uniques_index:
            self.validate_uniques_tab()

    def validate_uniques_tab(self):
        """Example validation method"""
        pass

    def save_all(self):
        """Save all tabs' configurations"""
        self.affixes_tab.save_all()
        # Add save calls for other tabs
        QMessageBox.information(self, "Saved", "All configurations saved successfully")
