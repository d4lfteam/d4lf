import logging
import sys
from pathlib import Path
from typing import override

from PyQt6.QtCore import QPoint, QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import QMainWindow

from src.profiles.editor.profile.tab import ProfileTab

BASE_DIR = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent.parent.parent
)

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)


class ProfileEditorWindow(QMainWindow):
    """Standalone window for Profile Editor."""

    def __init__(self, parent=None, profile_name: str | None = None, force_maximized: bool = False):
        super().__init__(parent)
        self.settings = QSettings("d4lf", "profile_editor")
        self._initial_profile = profile_name
        self._closing = False

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, on=True)
        self.setWindowTitle("Profile Editor")

        self.resize(self.settings.value("size", QSize(650, 800)))
        self.move(self.settings.value("pos", QPoint(0, 0)))

        if force_maximized or self.settings.value("maximized", "true") == "true":
            self.showMaximized()

        QTimer.singleShot(0, self._finish_construction)

    def _finish_construction(self):
        if self._closing:
            return
        self.profile_tab = ProfileTab(initial_profile_name=self._initial_profile)
        self.setCentralWidget(self.profile_tab)

    @override
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Save window size/position and check if profile needs saving."""
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())

        if a0 is None:
            return
        profile_tab = getattr(self, "profile_tab", None)
        if profile_tab is None:
            self._closing = True
            a0.accept()
        elif profile_tab.check_close_save():
            a0.accept()
        else:
            a0.ignore()
