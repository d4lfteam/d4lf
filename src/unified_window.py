import logging
import re

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget

from gui.activity_log_widget import ActivityLogWidget
from src.logger import create_formatter
from src.logger import setup as setup_logging
from src.logger import ThreadNameFilter


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
        import time

        from src import tts
        from src.cam import Cam
        from src.config.loader import IniConfigLoader
        from src.item.filter import Filter
        from src.main import check_for_proper_tts_configuration
        from src.overlay import Overlay
        from src.scripts.handler import ScriptHandler
        from src.utils.window import WindowSpec, start_detecting_window

        Filter().load_files()

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

        from PyQt6.QtWidgets import QApplication

        from src.config.loader import IniConfigLoader
        from src.gui.themes import DARK_THEME, LIGHT_THEME

        config = IniConfigLoader()
        theme_name = getattr(config.general, "theme", None) or "dark"

        stylesheet = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        QApplication.instance().setStyleSheet(stylesheet)

        setup_logging(enable_stdout=False)

        root_logger = logging.getLogger()

        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)

        self.console_handler = QtConsoleHandler()
        self.console_handler.setFormatter(create_formatter(colored=True))
        self.console_handler.setLevel(logging.DEBUG)
        self.console_handler.addFilter(ThreadNameFilter())

        self.activity_handler = QtActivityHandler()
        activity_formatter = logging.Formatter("%(message)s")
        self.activity_handler.setFormatter(activity_formatter)
        self.activity_handler.setLevel(logging.INFO)

        root_logger.addHandler(self.console_handler)
        root_logger.addHandler(self.activity_handler)
        root_logger.setLevel(logging.INFO)

        self.setWindowTitle("D4LF - Unified Window")
        self.setMinimumSize(800, 600)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.activity_tab = ActivityLogWidget(parent=self)
        self.console_tab = self.build_console_tab()

        self.tabs.addTab(self.activity_tab, "Activity Log")
        self.tabs.addTab(self.console_tab, "Console View")

        layout.addWidget(self.tabs)
        self.setCentralWidget(central)

        self.console_handler.log_signal.connect(self.console_output.append_ansi_text)
        self.activity_handler.log_signal.connect(self.activity_tab.log_viewer.appendPlainText)

        self.emit_startup_direct_to_console()

        self.thread = QThread()
        self.worker = BackendWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)

        self.restore_geometry()
        self.thread.start()

    def emit_startup_direct_to_console(self):
        from beautifultable import BeautifulTable

        from src import __version__
        from src.config.loader import IniConfigLoader

        line = f"============ D4 Loot Filter {__version__} ============"
        self.console_output.appendPlainText(line)

        table = BeautifulTable()
        table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)
        table.rows.append([IniConfigLoader().advanced_options.run_vision_mode, "Run/Stop Vision Mode"])

        if not IniConfigLoader().advanced_options.vision_mode_only:
            table.rows.append([IniConfigLoader().advanced_options.run_filter, "Run/Stop Auto Filter"])
            table.rows.append([
                IniConfigLoader().advanced_options.run_filter_force_refresh,
                "Force Run/Stop Filter, Resetting Item Status",
            ])
            table.rows.append([
                IniConfigLoader().advanced_options.force_refresh_only,
                "Reset Item Statuses Without A Filter After",
            ])
            table.rows.append([IniConfigLoader().advanced_options.move_to_inv, "Move Items From Chest To Inventory"])
            table.rows.append([IniConfigLoader().advanced_options.move_to_chest, "Move Items From Inventory To Chest"])

        table.rows.append([IniConfigLoader().advanced_options.exit_key, "Exit"])
        table.columns.header = ["hotkey", "action"]

        for line in str(table).splitlines():
            self.console_output.appendPlainText(line)

        self.console_output.appendPlainText("")

    def build_console_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.console_output = ANSIConsoleWidget()
        layout.addWidget(self.console_output)

        return widget

    def open_import_dialog(self):
        import logging

        from gui.importer_window import ImporterWindow

        LOGGER = logging.getLogger(__name__)

        try:
            if not hasattr(self, "import_window") or self.import_window is None:
                self.import_window = ImporterWindow()
                self.import_window.destroyed.connect(lambda: setattr(self, "import_window", None))
                self.import_window.show()
            else:
                self.import_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open importer: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Import Error", str(e))

    def open_settings_dialog(self):
        import logging

        from gui.config_window import ConfigWindow

        LOGGER = logging.getLogger(__name__)

        try:
            if not hasattr(self, "settings_window") or self.settings_window is None:
                self.settings_window = ConfigWindow(theme_changed_callback=self.apply_theme)
                self.settings_window.destroyed.connect(lambda: setattr(self, "settings_window", None))
                self.settings_window.show()
            else:
                self.settings_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open settings: {e}")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Settings Error", str(e))

    def open_profile_editor(self):
        from gui.profile_editor_window import ProfileEditorWindow

        if not hasattr(self, "editor_window") or self.editor_window is None:
            self.editor_window = ProfileEditorWindow()
            self.editor_window.destroyed.connect(lambda: setattr(self, "editor_window", None))
            self.editor_window.show()
        else:
            self.editor_window.activateWindow()

    def restore_geometry(self):
        from PyQt6.QtCore import QPoint, QSettings, QSize

        settings = QSettings("d4lf", "mainwindow")

        size = settings.value("size", QSize(1000, 800))
        pos = settings.value("pos", QPoint(100, 100))
        maximized = settings.value("maximized", "false") == "true"

        self.resize(size)
        self.move(pos)

        if maximized:
            self.showMaximized()

    def save_geometry(self):
        from PyQt6.QtCore import QSettings

        settings = QSettings("d4lf", "mainwindow")

        if not self.isMaximized():
            settings.setValue("size", self.size())
            settings.setValue("pos", self.pos())

        settings.setValue("maximized", self.isMaximized())

    def closeEvent(self, event):
        self.save_geometry()

        root_logger = logging.getLogger()
        root_logger.removeHandler(self.console_handler)
        root_logger.removeHandler(self.activity_handler)
        self.console_handler.setLevel(logging.CRITICAL + 1)
        self.activity_handler.setLevel(logging.CRITICAL + 1)

        logging.shutdown()
        super().closeEvent(event)

    def apply_theme(self):
        from PyQt6.QtWidgets import QApplication

        from src.config.loader import IniConfigLoader
        from src.gui.themes import DARK_THEME, LIGHT_THEME

        theme_name = IniConfigLoader().general.theme
        stylesheet = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        QApplication.instance().setStyleSheet(stylesheet)
