import logging
from pathlib import Path

from PyQt6.QtCore import QPoint, QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow

from src.gui.profile_tab import ProfileTab

ICON_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)


class ProfileEditorWindow(QMainWindow):
    """Standalone window for Profile Editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("d4lf", "profile_editor")

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("Profile Editor")

        self.resize(self.settings.value("size", QSize(650, 800)))
        self.move(self.settings.value("pos", QPoint(0, 0)))

        if self.settings.value("maximized", "true") == "true":
            self.showMaximized()

        # Defer heavy construction
        QTimer.singleShot(0, self._finish_construction)

    def _finish_construction(self):
        self.profile_tab = ProfileTab()
        self.setCentralWidget(self.profile_tab)
        self.profile_tab.show_tab()

    def closeEvent(self, event):
        """Save window size/position and check if profile needs saving."""
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())

        if self.profile_tab.check_close_save():
            event.accept()
        else:
            event.ignore()
