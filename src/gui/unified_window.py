import logging
import re
import sys
import time
from contextlib import suppress
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QSettings, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from src import __version__, tts
from src.autoupdater import notify_if_update
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.gui.activity_log_widget import ActivityLogWidget
from src.gui.config_window import ConfigWindow
from src.gui.importer_window import ImporterWindow
from src.gui.profile_editor_window import ProfileEditorWindow
from src.gui.themes import DARK_THEME, LIGHT_THEME
from src.item.filter import Filter
from src.logger import ThreadNameFilter, create_formatter
from src.logger import setup as setup_logging
from src.main import check_for_proper_tts_configuration
from src.overlay import Overlay
from src.scripts.handler import ScriptHandler
from src.utils.window import WindowSpec, start_detecting_window

BASE_DIR = (
    Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
)

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)

ANSI_PATTERN = re.compile(r"\x1b\[(\d+)(;\d+)*m")

ANSI_COLORS = {
    "30": "#000000",
    "31": "#AA0000",
    "32": "#00AA00",
    "33": "#AA5500",
    "34": "#0000AA",
    "35": "#AA00AA",
    "36": "#00AAAA",
    "37": "#AAAAAA",
    "90": "#555555",
    "91": "#FF5555",
    "92": "#55FF55",
    "93": "#FFFF55",
    "94": "#5555FF",
    "95": "#FF55FF",
    "96": "#55FFFF",
    "97": "#FFFFFF",
}


def ansi_to_html(text: str) -> str:
    html = ""
    last_end = 0
    current_color = None

    for match in ANSI_PATTERN.finditer(text):
        start, end = match.span()
        html += text[last_end:start].replace("<", "&lt;").replace(">", "&gt;")

        codes = match.group(0)[2:-1].split(";")
        for code in codes:
            if code in ANSI_COLORS:
                current_color = ANSI_COLORS[code]
            elif code == "0":
                current_color = None

        if current_color:
            html += f'<span style="color:{current_color}">'
        else:
            html += "</span>"

        last_end = end

    html += text[last_end:].replace("<", "&lt;").replace(">", "&gt;")

    if current_color:
        html += "</span>"

    return html


class ANSIConsoleWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("background-color: black; color: white; font-family: Consolas, monospace; font-size: 12px;")

    def append_ansi_text(self, text: str):
        html = ansi_to_html(text)
        self.appendHtml(html)
        self.moveCursor(QTextCursor.MoveOperation.End)


class QtConsoleHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)


class QtActivityHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)


class BackendWorker(QObject):
    finished = pyqtSignal()

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

        ScriptHandler()

        check_for_proper_tts_configuration()
        tts.start_connection()

        overlay = Overlay()
        overlay.run()

        self.finished.emit()


class UnifiedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Track child windows by type for singleton behavior
        self._config_window: ConfigWindow | None = None
        self._importer_window: ImporterWindow | None = None
        self._profile_editor_window: ProfileEditorWindow | None = None

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        # --- Theme setup ---
        config = IniConfigLoader()
        theme_name = getattr(config.general, "theme", None) or "dark"
        stylesheet = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        QApplication.instance().setStyleSheet(stylesheet)
        # --- Logging setup ---
        running_from_source = not getattr(sys, "frozen", False)
        root_logger = logging.getLogger()

        # Ensure file logging stays enabled. unified_window previously removed all handlers (including the file handler),
        # which stopped live log writing to d4lf/logs.
        if not any(getattr(h, "name", "") == "D4LF_FILE" for h in root_logger.handlers):
            setup_logging(log_level=config.advanced_options.log_lvl.value, enable_stdout=running_from_source)

        # Remove existing handlers, but keep file handler and (optionally) stdout when running from source
        for h in list(root_logger.handlers):
            if getattr(h, "name", "") == "D4LF_FILE":
                continue  # Keep file logging
            if running_from_source and isinstance(h, logging.StreamHandler) and h.stream == sys.stdout:
                continue  # Keep stdout handler for IDE terminal
            root_logger.removeHandler(h)

        self.console_handler = QtConsoleHandler()
        self.console_handler.setFormatter(create_formatter(colored=True))
        self.console_handler.setLevel(config.advanced_options.log_lvl.value.upper())
        self.console_handler.addFilter(ThreadNameFilter())

        self.activity_handler = QtActivityHandler()
        activity_formatter = logging.Formatter("%(message)s")
        self.activity_handler.setFormatter(activity_formatter)
        self.activity_handler.setLevel(logging.INFO)

        root_logger.addHandler(self.console_handler)
        root_logger.addHandler(self.activity_handler)
        root_logger.setLevel(config.advanced_options.log_lvl.value.upper())

        # --- Window setup: version in title bar ---
        self.setWindowTitle(f"D4LF - Diablo 4 Loot Filter v{__version__}")
        self.setMinimumSize(800, 600)

        central = QWidget()
        layout = QVBoxLayout(central)

        # ActivityLogWidget is the whole page (with buttons + hotkeys)
        self.activity_tab = ActivityLogWidget(parent=self)
        layout.addWidget(self.activity_tab)
        self.setCentralWidget(central)

        # --- Build console widget and inject stack into ActivityLogWidget ---
        # 1) Build console widget
        self.console_output = ANSIConsoleWidget()

        # 2) Get the layout of ActivityLogWidget
        act_layout = self.activity_tab.layout()

        # 3) Find the index of the existing log_viewer
        #    (the little log box under "Activity Log:")
        idx = act_layout.indexOf(self.activity_tab.log_viewer)

        # 4) Remove the original log_viewer from layout
        act_layout.removeWidget(self.activity_tab.log_viewer)

        # 5) Create a stacked widget that holds:
        #    - original log_viewer
        #    - console_output
        self.log_stack = QStackedWidget()
        self.log_stack.addWidget(self.activity_tab.log_viewer)  # index 0: Log View
        self.log_stack.addWidget(self.console_output)  # index 1: Console View

        # 6) Insert the stack back where the log_viewer was
        act_layout.insertWidget(idx, self.log_stack)

        # 7) Create a small tab bar for Log / Console and put it just above the stack
        self.log_tabbar = QTabBar()
        self.log_tabbar.addTab("Log View")
        self.log_tabbar.addTab("Console View")

        # Insert the tabbar just before the stack
        act_layout.insertWidget(idx, self.log_tabbar)

        # 8) Wire tabbar to stacked widget
        self.log_tabbar.currentChanged.connect(self.log_stack.setCurrentIndex)

        # --- Logging connections ---
        # Console handler → console_output
        self.console_handler.log_signal.connect(self.console_output.append_ansi_text)
        # Activity handler → original log_viewer
        self.activity_handler.log_signal.connect(self.activity_tab.log_viewer.appendPlainText)

        # --- Startup banner ---
        self.emit_startup_direct_to_console()

        # --- Backend worker thread ---
        self.thread = QThread()
        self.worker = BackendWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)

        # --- Final setup ---
        self.restore_geometry()
        self.thread.start()

    def _show_singleton_modal(self, window_attr: str, window_class, *args, **kwargs):
        """Helper to show a singleton modal window.

        If window already exists and is visible, bring it to front.
        Otherwise create a new one.
        """
        existing_window = getattr(self, window_attr)

        # If window exists and is visible, just bring it to front
        if existing_window is not None and existing_window.isVisible():
            existing_window.raise_()
            existing_window.activateWindow()
            return existing_window

        # Create new window
        win = window_class(*args, **kwargs)
        win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Make it modal
        win.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Track the window
        setattr(self, window_attr, win)

        # Clear reference when window is destroyed
        def on_destroyed():
            setattr(self, window_attr, None)

        win.destroyed.connect(on_destroyed)

        win.show()
        return win

    def open_import_dialog(self):
        try:
            self._show_singleton_modal("_importer_window", ImporterWindow)
        except Exception as e:
            LOGGER.error(f"Failed to open importer: {e}")
            QMessageBox.critical(self, "Import Error", str(e))

    def open_settings_dialog(self):
        try:
            self._show_singleton_modal("_config_window", ConfigWindow, theme_changed_callback=self.apply_theme)
        except Exception as e:
            LOGGER.error(f"Failed to open settings: {e}")
            QMessageBox.critical(self, "Settings Error", str(e))

    def open_profile_editor(self):
        try:
            self._show_singleton_modal("_profile_editor_window", ProfileEditorWindow)
        except Exception as e:
            LOGGER.error(f"Failed to open profile editor: {e}")

    def restore_geometry(self):

        settings = QSettings("d4lf", "mainwindow")

        size = settings.value("size", QSize(1000, 800))
        pos = settings.value("pos", QPoint(100, 100))
        maximized = settings.value("maximized", "false") == "true"

        self.resize(size)
        self.move(pos)

        if maximized:
            self.showMaximized()

        selected = settings.value("selected_view", 0, int)
        self.log_tabbar.setCurrentIndex(selected)
        self.log_stack.setCurrentIndex(selected)

    def save_geometry(self):
        settings = QSettings("d4lf", "mainwindow")

        if not self.isMaximized():
            settings.setValue("size", self.size())
            settings.setValue("pos", self.pos())

        settings.setValue("maximized", self.isMaximized())
        settings.setValue("selected_view", self.log_tabbar.currentIndex())

    def closeEvent(self, event):
        # Close all child windows
        for window_attr in ("_config_window", "_importer_window", "_profile_editor_window"):
            win = getattr(self, window_attr)
            if win is not None:
                with suppress(Exception):
                    win.close()

        # --- Existing behavior ---
        self.save_geometry()

        root_logger = logging.getLogger()

        with suppress(Exception):
            root_logger.removeHandler(self.console_handler)
            root_logger.removeHandler(self.activity_handler)

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
        self.console_output.appendPlainText("")  # one blank line for spacing

    def apply_theme(self):
        theme_name = IniConfigLoader().general.theme
        stylesheet = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        QApplication.instance().setStyleSheet(stylesheet)
