import logging

from PyQt6.QtCore import QPoint, QSettings, QSize
from PyQt6.QtWidgets import QMainWindow

from src import __version__
from src.gui.config_tab import ConfigTab

LOGGER = logging.getLogger(__name__)


class ConfigWindow(QMainWindow):
    """Standalone window for Config/Settings."""

    def __init__(self, theme_changed_callback=None):
        super().__init__()
        self.theme_changed_callback = theme_changed_callback
        self.settings = QSettings("d4lf", "config")

        self.setWindowTitle(f"Settings - D4LF v{__version__}")

        self.resize(self.settings.value("size", QSize(650, 800)))
        self.move(self.settings.value("pos", QPoint(0, 0)))

        if self.settings.value("maximized", "false") == "true":
            self.showMaximized()

        # Create initial config tab
        self.config_tab = ConfigTab(theme_changed_callback=self._on_theme_changed)
        self.setCentralWidget(self.config_tab)

    def _on_theme_changed(self):
        if self.theme_changed_callback:
            self.theme_changed_callback()

    def _rebuild_tab(self):
        old_tab = self.config_tab
        self.config_tab = ConfigTab(theme_changed_callback=self._on_theme_changed)
        self.setCentralWidget(self.config_tab)
        old_tab.deleteLater()

    def closeEvent(self, event):
        """Save window size/position."""
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())
        event.accept()
