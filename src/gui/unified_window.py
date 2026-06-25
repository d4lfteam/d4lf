import logging
import sys
import time
from contextlib import suppress
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QPoint, QSettings, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QWidget,
)

from src import __version__, tts
from src.autoupdater import notify_if_update
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.reload_groups import LOG_LEVEL_SETTING_KEYS, has_any_changed
from src.gui.importer_window import ImporterWindow
from src.gui.models.activity_log_widget import ActivityLogWidget, ANSIConsoleWidget, QtConsoleHandler
from src.gui.profile_editor_window import ProfileEditorWindow
from src.gui.settings_window import ConfigWindow
from src.gui.themes import DARK_THEME_TEMPLATE, LIGHT_THEME_TEMPLATE
from src.item.filter import Filter
from src.logger import apply_log_level, create_formatter
from src.logger import setup as setup_logging
from src.main import check_for_proper_tts_configuration
from src.overlay import Overlay
from src.scripts.common import get_filter_colors
from src.scripts.handler import ScriptHandler
from src.utils.window import WindowSpec, start_detecting_window

BASE_DIR = (
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
)

ICON_PATH = BASE_DIR / "assets" / "logo.png"


def get_asset_path(filename: str) -> Path:
    """Resilient helper to find assets in root/assets or src/assets, handling case sensitivity."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "assets" / filename

    # Search paths: 3 parents (root from gui/) and 2 parents (src from gui/)
    for parent_level in [2, 3]:
        base = Path(__file__).resolve().parents[parent_level]
        # Try exact name, then lowercase version
        for name in [filename, filename.lower()]:
            p = base / "assets" / name
            if p.exists():
                return p
    # Fallback to the root path even if not found
    return Path(__file__).resolve().parents[2] / "assets" / filename


DISCORD_ICON = get_asset_path("Discord.png")
GITHUB_ICON = get_asset_path("Github.png")

LOGGER = logging.getLogger(__name__)


class BackendWorker(QObject):
    finished = pyqtSignal()
    script_handler: ScriptHandler | None = None

    def run(self):
        Filter().load_files()

        running_from_source = not getattr(sys, "frozen", False)
        if running_from_source:
            LOGGER.debug("Skipping autoupdate check as code is being run from source.")
        else:
            notify_if_update()

        win_spec = WindowSpec(IniConfigLoader().advanced_options.process_name)
        start_detecting_window(win_spec)

        while not Cam().is_offset_set():
            time.sleep(0.2)

        time.sleep(0.5)

        self.script_handler = ScriptHandler()

        check_for_proper_tts_configuration()
        tts.start_connection()

        overlay = Overlay()
        overlay.run()

        self.finished.emit()


class UnifiedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._child_windows: dict[str, QMainWindow] = {}
        self._config = IniConfigLoader()

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.apply_theme()
        self._setup_logging()
        self._setup_ui()
        self._setup_tray()
        self._init_backend()
        self.restore_geometry()

        # Polling timer to keep the Dashboard status indicators in sync with the backend
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_dashboard_status)
        self._status_timer.start(500)

    def _setup_logging(self):
        running_from_source = not getattr(sys, "frozen", False)
        root_logger = logging.getLogger()
        adv = self._config.advanced_options

        if not any(getattr(h, "name", "") == "D4LF_FILE" for h in root_logger.handlers):
            setup_logging(
                log_level=adv.log_lvl.value,
                enable_stdout=running_from_source,
                technical=adv.technical_log_info,
                timestamp=adv.log_timestamp,
            )

        for h in list(root_logger.handlers):
            if getattr(h, "name", "") == "D4LF_FILE":
                continue  # Keep file logging
            root_logger.removeHandler(h)

        # Single unified Qt handler for both Dashboard and Full Logs
        self.console_handler = QtConsoleHandler()
        self.console_handler.name = "QT_CONSOLE"
        self.console_handler.setFormatter(
            create_formatter(colored=True, technical=adv.technical_log_info, timestamp=adv.log_timestamp)
        )
        self.console_handler.setLevel(adv.log_lvl.value.upper())

        root_logger.addHandler(self.console_handler)
        # Root is always DEBUG; the handlers above (Console/QT) filter based on user settings
        root_logger.setLevel(logging.DEBUG)

        # Apply log level changes live, independently of the backend's wait-for-D4 loop.
        self._config.register_change_listener(self._on_config_changed_log_level)

    def _on_config_changed_log_level(self, changed_keys) -> None:
        if not has_any_changed(changed_keys, LOG_LEVEL_SETTING_KEYS):
            return
        adv = self._config.advanced_options
        new_level = adv.log_lvl.value.upper()
        formatter = create_formatter(colored=True, technical=adv.technical_log_info, timestamp=adv.log_timestamp)
        apply_log_level(new_level, skip_handler_names={"D4LF_FILE"}, formatter=formatter)
        LOGGER.info(
            "Updated log settings (Level: %s, Tech: %s, TS: %s)", new_level, adv.technical_log_info, adv.log_timestamp
        )

    def _setup_ui(self):
        self.setWindowTitle(f"D4LF - Diablo 4 Loot Filter v{__version__}")
        self.setMinimumSize(800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.activity_tab = ActivityLogWidget(parent=self)
        self.console_output = ANSIConsoleWidget()

        self.tabs.addTab(self.activity_tab, "Dashboard")
        self.tabs.addTab(self.console_output, "Full Logs")
        self._setup_tab_corner_widgets()

        # Both tabs receive the same unified stream
        self.console_handler.log_signal.connect(self.console_output.append_ansi_text)
        self.console_handler.log_signal.connect(self.activity_tab.log_viewer.append_ansi_text)

        self._emit_deferred_config_cleanup_logs(self._config)

    def _setup_tab_corner_widgets(self):
        """Add social buttons to the top right of the tab bar."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 15, 0)
        layout.setSpacing(15)

        # System Status Indicators
        self.vision_indicator = QLabel("Vision Mode: STOPPED")
        self.vision_indicator.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 10pt;")
        self.tts_indicator = QLabel("TTS: Disconnected")
        self.tts_indicator.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 10pt;")

        layout.addWidget(self.vision_indicator)
        layout.addWidget(self.tts_indicator)

        discord_btn = QPushButton()
        self._setup_social_button(discord_btn, DISCORD_ICON, "https://discord.gg/YyzaPhAN6T")
        github_btn = QPushButton()
        self._setup_social_button(github_btn, GITHUB_ICON, "https://github.com/d4lfteam/d4lf")

        layout.addWidget(discord_btn)
        layout.addWidget(github_btn)
        self.tabs.setCornerWidget(container, Qt.Corner.TopRightCorner)

    def _setup_social_button(self, btn: QPushButton, icon_path: Path, url: str):
        # Double check existence and check for lowercase fallback on-the-fly
        final_path = icon_path
        if not final_path.exists():
            alt_path = icon_path.parent / icon_path.name.lower()
            if alt_path.exists():
                final_path = alt_path

        if final_path.exists():
            btn.setIcon(QIcon(str(final_path)))
            btn.setIconSize(QSize(24, 24))
        else:
            btn.setText("D" if "discord" in url else "G")
        btn.setFixedSize(30, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(url)
        btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; } QPushButton:hover { background-color: #333; border-radius: 4px; }"
        )
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))

    def _refresh_dashboard_status(self):
        """Poll backend states and update the Dashboard labels."""
        self.update_tts_status(tts.CONNECTED)
        if self.worker and self.worker.script_handler:
            self.update_vision_status(self.worker.script_handler.vision_mode.running())

    def update_vision_status(self, is_running: bool):
        if is_running:
            self.vision_indicator.setText("Vision Mode: RUNNING")
            self.vision_indicator.setStyleSheet("color: #23fc5d; font-weight: bold; font-size: 10pt;")
        else:
            self.vision_indicator.setText("Vision Mode: STOPPED")
            self.vision_indicator.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 10pt;")

    def update_tts_status(self, connected: bool):
        if connected:
            self.tts_indicator.setText("TTS: Connected")
            self.tts_indicator.setStyleSheet("color: #23fc5d; font-weight: bold; font-size: 10pt;")
        else:
            self.tts_indicator.setText("TTS: Disconnected")
            self.tts_indicator.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 10pt;")

    def _init_backend(self):
        self.thread = QThread()
        self.worker = BackendWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()

    def _show_singleton_modal(self, key: str, window_class, *args, **kwargs):
        existing_window = self._child_windows.get(key)

        # If window exists and is visible, just bring it to front
        if existing_window is not None and existing_window.isVisible():
            existing_window.raise_()
            existing_window.activateWindow()
            return existing_window
        win = window_class(*args, **kwargs)
        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        win.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._child_windows[key] = win
        win.destroyed.connect(lambda: self._child_windows.pop(key, None))

        win.show()
        return win

    def _emit_deferred_config_cleanup_logs(self, config):
        for record in config.consume_deferred_cleanup_log_records():
            if not logging.getLogger(record.name).isEnabledFor(record.levelno):
                continue
            if record.levelno >= self.console_handler.level:
                self.console_handler.handle(record)

    def open_import_dialog(self):
        win = self._show_singleton_modal("importer", ImporterWindow)
        win.import_completed.connect(self.activity_tab.refresh_profiles, Qt.ConnectionType.UniqueConnection)

    def open_settings_dialog(self):
        self._show_singleton_modal("config", ConfigWindow, theme_changed_callback=self.apply_theme)

    def open_profile_editor(self, profile_name: str | None = None):
        self._show_singleton_modal("editor", ProfileEditorWindow, profile_name=profile_name)

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
        # Using False as a positional argument for defaultValue is required by the QSettings API
        self.activity_tab.minimize_to_tray_cb.setChecked(
            settings.value("minimize_to_tray", False, type=bool)  # noqa: FBT003
        )

    def save_geometry(self):
        settings = QSettings("d4lf", "mainwindow")

        if not self.isMaximized():
            settings.setValue("size", self.size())
            settings.setValue("pos", self.pos())

        settings.setValue("maximized", self.isMaximized())
        settings.setValue("selected_tab", self.tabs.currentIndex())
        settings.setValue("minimize_to_tray", self.activity_tab.minimize_to_tray_cb.isChecked())

    def _setup_tray(self):
        """Initialize the system tray icon and its context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        if ICON_PATH.exists():
            self.tray_icon.setIcon(QIcon(str(ICON_PATH)))

        tray_menu = QMenu()
        restore_action = tray_menu.addAction("Restore")
        restore_action.triggered.connect(self._restore_from_tray)

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("Exit")
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

    def changeEvent(self, event: QEvent):  # noqa: N802
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
            and self.activity_tab.minimize_to_tray_cb.isChecked()
        ):
            self.hide()
        super().changeEvent(event)

    def closeEvent(self, event):  # noqa: N802
        for win in list(self._child_windows.values()):
            with suppress(Exception):
                win.close()

        self.save_geometry()
        root_logger = logging.getLogger()
        with suppress(Exception):
            root_logger.removeHandler(self.console_handler)
        with suppress(Exception):
            logging._handlerList.clear()

        super().closeEvent(event)

    def emit_startup_direct_to_console(self):
        banner = (
            "═══════════════════════════════════════════════════════════════════════════════\n"
            "D4LF - Diablo 4 Loot Filter\n"
            "═══════════════════════════════════════════════════════════════════════════════"
        )
        self.console_output.appendPlainText(banner)
        self.console_output.appendPlainText("")

    def apply_theme(self):
        theme_name = IniConfigLoader().general.theme
        accent_color = get_filter_colors().matched
        template = DARK_THEME_TEMPLATE if theme_name == "dark" else LIGHT_THEME_TEMPLATE
        stylesheet = template.replace("{accent}", accent_color)

        QApplication.instance().setStyleSheet(stylesheet)
