import logging

from PyQt6.QtCore import QPoint, QSettings, QSize
from PyQt6.QtWidgets import QMainWindow

from src import __version__
from src.config.loader import IniConfigLoader
from src.gui.config_tab import ConfigTab
from src.gui.themes import DARK_THEME, LIGHT_THEME

LOGGER = logging.getLogger(__name__)


class ConfigWindow(QMainWindow):
    """Standalone window for Config/Settings"""

    def __init__(self, theme_changed_callback=None):
        super().__init__()
        self.theme_changed_callback = theme_changed_callback
        self.settings = QSettings("d4lf", "config")

        self.setWindowTitle(f"Settings - D4LF v{__version__}")

        self.resize(self.settings.value("size", QSize(650, 800)))
        self.move(self.settings.value("pos", QPoint(0, 0)))

        if self.settings.value("maximized", "false") == "true":
            self.showMaximized()

        # Apply theme
        self._apply_theme()

        # Create config tab and set as central widget
        self.config_tab = ConfigTab(theme_changed_callback=self._on_theme_changed)
        self.setCentralWidget(self.config_tab)

    def _apply_theme(self):
        """Apply theme from settings"""
        config = IniConfigLoader()
        theme = config.general.theme.value
        if theme == "dark":
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)

    def _on_theme_changed(self):
        """Called when theme changes in config tab"""
        # Reload theme for this window
        self._apply_theme()

        # Notify main window if callback provided
        if self.theme_changed_callback:
            self.theme_changed_callback()

    def closeEvent(self, event):
        """Save window size/position"""
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())
        event.accept()
