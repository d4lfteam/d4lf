from PyQt6.QtWidgets import (QWidget, QTabWidget, QMessageBox)
from PyQt6.QtCore import Qt
from src.config.models import ProfileModel
from src.gui.affixes_tab import AffixesTab
from src.gui.sigils_tab import SigilsTab
from src.gui.tributes_tab import TributesTab
from src.gui.importer.common import _to_yaml_str
from src.config.loader import IniConfigLoader
from src import __version__

import datetime
import logging
import re

LOGGER = logging.getLogger(__name__)

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
        self.affixes_tab = AffixesTab(self.profile_model.Affixes)
        self.sigils_tab = SigilsTab(self.profile_model.Sigils)  # To be implemented
        self.tributes_tab = TributesTab(self.profile_model.Tributes)  # To be implemented
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
        self.save_to_yaml(self.profile_model.name + "_custom", self.profile_model, "custom")

        QMessageBox.information(self, "Saved", "All configurations saved successfully")

    def save_to_yaml(self, file_name: str, profile: ProfileModel, url : str):
            file_name = file_name.replace("'", "")
            file_name = re.sub(r"\W", "_", file_name)
            file_name = re.sub(r"_+", "_", file_name).rstrip("_")
            save_path = IniConfigLoader().user_dir / f"profiles/{file_name}.yaml"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as file:
                file.write(f"# {url}\n")
                file.write(f"# {datetime.datetime.now(tz=datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')} (v{__version__})\n")
                file.write(
                    _to_yaml_str(
                        profile,
                        exclude_unset=not IniConfigLoader().general.full_dump,
                        exclude={"name"},
                    )
                )
            LOGGER.info(f"Created profile {save_path}")
