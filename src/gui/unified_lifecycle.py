import logging
from contextlib import suppress
from typing import Any, override

from PyQt6.QtCore import QEvent, QPoint, QSettings, QSize
from PyQt6.QtGui import QAction, QCloseEvent, QIcon
from PyQt6.QtWidgets import QMainWindow, QMenu, QSystemTrayIcon, QTabWidget

from src.gui.unified_shell import ICON_PATH


class UnifiedWindowLifecycle(QMainWindow):
    _child_windows: dict[str, QMainWindow]
    activity_tab: Any
    console_handler: Any
    tabs: QTabWidget

    def _setup_tray(self):
        """Initialize the system tray icon and its context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        if ICON_PATH.exists():
            self.tray_icon.setIcon(QIcon(str(ICON_PATH)))

        tray_menu = QMenu()
        restore_action = QAction("Restore", tray_menu)
        tray_menu.addAction(restore_action)
        restore_action.triggered.connect(self._restore_from_tray)
        tray_menu.addSeparator()
        exit_action = QAction("Exit", tray_menu)
        tray_menu.addAction(exit_action)
        exit_action.triggered.connect(self.close)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.setToolTip("D4 Loot Filter")
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()

    def restore_geometry(self):
        settings = QSettings("d4lf", "mainwindow")
        size = settings.value("size", QSize(1000, 800))
        pos = settings.value("pos", QPoint(100, 100))
        maximized = settings.value("maximized", "false") == "true"
        self.resize(size)
        self.move(pos)
        if maximized:
            self.showMaximized()
        self.tabs.setCurrentIndex(settings.value("selected_tab", 0, int))
        # Using False as a positional argument for defaultValue is required by the QSettings API.
        self.activity_tab.minimize_to_tray_cb.setChecked(
            settings.value("minimize_to_tray", False, type=bool)  # ruff:ignore[boolean-positional-value-in-call]
        )

    def save_geometry(self):
        settings = QSettings("d4lf", "mainwindow")
        if not self.isMaximized():
            settings.setValue("size", self.size())
            settings.setValue("pos", self.pos())
        settings.setValue("maximized", self.isMaximized())
        settings.setValue("selected_tab", self.tabs.currentIndex())
        settings.setValue("minimize_to_tray", self.activity_tab.minimize_to_tray_cb.isChecked())

    @override
    def changeEvent(self, a0: QEvent | None):
        # PyQt exposes `a0` as a keyword, so the override must retain that public name.
        event = a0
        if (
            event is not None
            and event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
            and self.activity_tab.minimize_to_tray_cb.isChecked()
        ):
            self.hide()
        super().changeEvent(event)

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        # PyQt exposes `a0` as a keyword, so the override must retain that public name.
        event = a0
        for win in list(self._child_windows.values()):
            with suppress(Exception):
                win.close()
        self.save_geometry()
        root_logger = logging.getLogger()
        with suppress(Exception):
            root_logger.removeHandler(self.console_handler)
        super().closeEvent(event)
