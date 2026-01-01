import logging

from PyQt6.QtCore import QPoint, QSettings, QSize
from PyQt6.QtWidgets import QMainWindow

from src import __version__
from src.config.loader import IniConfigLoader
from src.gui.profile_tab import ProfileTab
from src.gui.themes import DARK_THEME, LIGHT_THEME

LOGGER = logging.getLogger(__name__)


class ProfileEditorWindow(QMainWindow):
    """Standalone window for Profile Editor"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("d4lf", "profile_editor")

        self.setWindowTitle(f"Profile Editor - D4LF v{__version__}")

        self.resize(self.settings.value("size", QSize(650, 800)))
        self.move(self.settings.value("pos", QPoint(0, 0)))

        if self.settings.value("maximized", "true") == "true":
            self.showMaximized()

        # Apply theme
        self._apply_theme()

        # Create profile tab and set as central widget
        self.profile_tab = ProfileTab()
        self.setCentralWidget(self.profile_tab)

        # Load the last profile
        self.profile_tab.show_tab()

    def _apply_theme(self):
        """Apply theme from settings"""
        config = IniConfigLoader()
        theme = config.general.theme.value
        if theme == "dark":
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)

    def closeEvent(self, event):
        """Save window size/position and check if profile needs saving"""
        # Write window size, position, and maximized status to config
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())

        # Check if profile needs to be saved before closing
        if self.profile_tab.check_close_save():
            event.accept()
        else:
            event.ignore()
