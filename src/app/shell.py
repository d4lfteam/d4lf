"""Unified desktop shell composed from public capability interfaces."""

import logging
import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QWidget,
)

from src import __version__
from src.app.assets import DISCORD_ICON, GITHUB_ICON, ICON_PATH
from src.app.backend import BackendWorker, get_perception_module
from src.app.dashboard import ActivityLogWidget
from src.app.lifecycle import UnifiedWindowLifecycle
from src.desktop.activity import ANSIConsoleWidget, QtLogHandler
from src.desktop.themes import DARK_THEME_TEMPLATE, LIGHT_THEME_TEMPLATE
from src.desktop.widgets import set_accent_color
from src.importing import create_importer_window
from src.logger import (
    apply_log_level,
    consume_startup_log_records,
    create_formatter,
    is_configured,
    remove_transient_gui_handlers,
)
from src.logger import setup as setup_logging
from src.loot import get_filter_colors
from src.profiles import create_profile_editor_window
from src.settings import (
    LOG_LEVEL_SETTING_KEYS,
    SettingsLoadError,
    create_settings_window,
    get_settings,
    has_any_changed,
)

if TYPE_CHECKING:
    from src.item import ProfileLoadReport

LOGGER = logging.getLogger(__name__)
perception_module = get_perception_module()


class UnifiedMainWindow(UnifiedWindowLifecycle):
    profile_load_report_signal = pyqtSignal(object)
    settings_load_error_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.profile_load_report_signal.connect(self._on_profile_load_report)
        self.settings_load_error_signal.connect(self._on_settings_load_error)
        self._child_windows: dict[str, QMainWindow] = {}
        self._config = get_settings()
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.apply_theme()
        self._setup_logging()
        self._setup_ui()
        self._setup_tray()
        self._init_backend()
        self.restore_geometry()
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_dashboard_status)
        self._status_timer.start(500)

    def _setup_logging(self):
        running_from_source = not getattr(sys, "frozen", False)
        root_logger = logging.getLogger()
        adv = self._config.advanced_options
        if not is_configured():
            setup_logging(
                log_level=adv.log_lvl.value,
                enable_stdout=running_from_source,
                technical=adv.technical_log_info,
                timestamp=adv.log_timestamp,
                buffer_startup=True,
            )
        remove_transient_gui_handlers(root_logger)
        self.console_handler = QtLogHandler()
        self.console_handler.name = "QT_CONSOLE"
        self.console_handler.setFormatter(
            create_formatter(colored=True, technical=adv.technical_log_info, timestamp=adv.log_timestamp)
        )
        self.console_handler.setLevel(adv.log_lvl.value.upper())
        root_logger.addHandler(self.console_handler)
        root_logger.setLevel(logging.DEBUG)
        self._config.register_change_listener(self._on_config_changed_log_level)
        self._config.register_load_error_listener(self._queue_settings_load_error)

    def _queue_settings_load_error(self, error: SettingsLoadError) -> None:
        self.settings_load_error_signal.emit(error)

    def _on_settings_load_error(self, error: SettingsLoadError) -> None:
        """Report a hot-reload failure without interrupting the game window."""
        if hasattr(self, "tray_icon"):
            self.tray_icon.showMessage(
                "D4LF settings reload failed",
                f"Could not reload {error.config_path.name}; see the Activity log ({error.log_path}).",
                QSystemTrayIcon.MessageIcon.Warning,
                10000,
            )

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
        self.console_handler.log_signal.connect(self.console_output.append_ansi_text)
        self.console_handler.log_signal.connect(self.activity_tab.log_viewer.append_ansi_text)
        self.emit_startup_direct_to_console()
        self._emit_startup_logs()
        self._emit_deferred_config_cleanup_logs(self._config)

    def _setup_tab_corner_widgets(self):
        """Add status indicators and social buttons to the tab bar."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 15, 0)
        layout.setSpacing(15)
        if sys.platform == "win32":
            self.vision_indicator = QLabel("Vision Mode: STOPPED")
            self.tts_indicator = QLabel("TTS: Disconnected")
            style = "color: #ff4d4d; font-weight: bold; font-size: 10pt;"
        else:
            self.vision_indicator = QLabel("Vision Mode: Disabled (GUI-only)")
            self.tts_indicator = QLabel("TTS: Disabled (GUI-only)")
            style = "color: #b0b0b0; font-weight: bold; font-size: 10pt;"
        self.vision_indicator.setStyleSheet(style)
        self.tts_indicator.setStyleSheet(style)
        layout.addWidget(self.vision_indicator)
        layout.addWidget(self.tts_indicator)
        for icon, url in (
            (DISCORD_ICON, "https://discord.gg/YyzaPhAN6T"),
            (GITHUB_ICON, "https://github.com/d4lfteam/d4lf"),
        ):
            button = QPushButton()
            self._setup_social_button(button, icon, url)
            layout.addWidget(button)
        self.tabs.setCornerWidget(container, Qt.Corner.TopRightCorner)

    def _setup_social_button(self, btn, icon_path, url: str):
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
        self.update_tts_status(perception_module.is_connected() if perception_module is not None else None)
        if self.worker and self.worker.script_handler:
            self.update_vision_status(self.worker.script_handler.vision_mode.running())

    def update_vision_status(self, is_running: bool | None):
        if is_running is None:
            self.vision_indicator.setText("Vision Mode: Disabled (GUI-only)")
            self.vision_indicator.setStyleSheet("color: #b0b0b0; font-weight: bold; font-size: 10pt;")
            return
        self.vision_indicator.setText(f"Vision Mode: {'RUNNING' if is_running else 'STOPPED'}")
        self.vision_indicator.setStyleSheet(
            f"color: {'#23fc5d' if is_running else '#ff4d4d'}; font-weight: bold; font-size: 10pt;"
        )

    def update_tts_status(self, connected: bool | None):
        if connected is None:
            self.tts_indicator.setText("TTS: Disabled (GUI-only)")
            self.tts_indicator.setStyleSheet("color: #b0b0b0; font-weight: bold; font-size: 10pt;")
            return
        self.tts_indicator.setText(f"TTS: {'Connected' if connected else 'Disconnected'}")
        self.tts_indicator.setStyleSheet(
            f"color: {'#23fc5d' if connected else '#ff4d4d'}; font-weight: bold; font-size: 10pt;"
        )

    def _init_backend(self):
        if sys.platform != "win32":
            self._backend_thread = None
            self.worker = None
            self.update_vision_status(None)
            self.update_tts_status(None)
            return
        from src.item import Filter  # ruff:ignore[import-outside-top-level]

        Filter().register_profile_failure_listener(self._queue_profile_load_report)
        self._backend_thread = QThread()
        self.worker = BackendWorker()
        self.worker.moveToThread(self._backend_thread)
        self._backend_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._backend_thread.quit)
        self._backend_thread.start()

    def _queue_profile_load_report(self, report: ProfileLoadReport) -> None:
        self.profile_load_report_signal.emit(report)

    def _on_profile_load_report(self, report: ProfileLoadReport) -> None:
        if hasattr(self, "tray_icon"):
            self.tray_icon.showMessage(
                "D4LF profile loading", report.message, QSystemTrayIcon.MessageIcon.Warning, 10000
            )

    def _show_singleton_modal(self, key: str, window_class, *args, **kwargs):
        existing_window = self._child_windows.get(key)
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
            if (
                logging.getLogger(record.name).isEnabledFor(record.levelno)
                and record.levelno >= self.console_handler.level
            ):
                self.console_handler.handle(record)

    def _emit_startup_logs(self):
        for record in consume_startup_log_records():
            if (
                logging.getLogger(record.name).isEnabledFor(record.levelno)
                and record.levelno >= self.console_handler.level
            ):
                self.console_handler.handle(record)

    def open_import_dialog(self):
        win = self._show_singleton_modal("importer", create_importer_window, accent_color=get_filter_colors().matched)
        win.import_completed.connect(self.activity_tab.refresh_profiles, Qt.ConnectionType.UniqueConnection)

    def open_settings_dialog(self):
        set_accent_color(get_filter_colors().matched)
        self._show_singleton_modal(
            "config",
            create_settings_window,
            theme_changed_callback=self.apply_theme,
            force_maximized=self.isMaximized(),
        )

    def open_profile_editor(self, profile_name: str | None = None):
        self._show_singleton_modal(
            "editor", create_profile_editor_window, profile_name=profile_name, force_maximized=self.isMaximized()
        )

    def emit_startup_direct_to_console(self):
        self.console_output.append_ansi_text(
            "═══════════════════════════════════════════════════════════════════════════════\n"
            "D4LF - Diablo 4 Loot Filter\n"
            "═══════════════════════════════════════════════════════════════════════════════"
        )
        self.console_output.append_ansi_text("")

    def apply_theme(self):
        theme_name = get_settings().general.theme
        accent_color = get_filter_colors().matched
        set_accent_color(accent_color)
        template = DARK_THEME_TEMPLATE if theme_name == "dark" else LIGHT_THEME_TEMPLATE
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(template.replace("{accent}", accent_color))
