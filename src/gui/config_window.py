import logging
from pathlib import Path

from PyQt6.QtCore import QPoint, QSettings, QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow

from src.gui.config_tab import ConfigTab

ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)


class ConfigWindow(QMainWindow):
    """Standalone window for Config/Settings."""

    def __init__(self, parent=None, theme_changed_callback=None):
        super().__init__(parent)

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.theme_changed_callback = theme_changed_callback
        self.settings = QSettings("d4lf", "config")

        self.setWindowTitle("Settings")

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

        # Rebuild the tab so the settings window updates visually too
        self._rebuild_tab()

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
