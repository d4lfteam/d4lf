"""Main Window for d4lf - integrates scanning overlay with GUI controls.

Shows log output and provides access to Import, Settings, and Profile Editor.
"""

import logging
from pathlib import Path

from PyQt6.QtCore import QPoint, QSettings, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.config.loader import IniConfigLoader
from src.gui.config_window import ConfigWindow
from src.gui.importer_window import ImporterWindow
from src.gui.profile_editor_window import ProfileEditorWindow
from src.gui.themes import DARK_THEME, LIGHT_THEME
from src.logger import LOG_DIR

BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOGGER = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Custom logging handler that emits log records to Qt signal."""

    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class MainWindow(QMainWindow):
    """The full main window object.

    The main window houses:
    - Top: Real-time log viewer showing d4lf scanning output
    - Bottom: Three buttons for Import Profile, Settings, and Edit Profile
    """

    # Signal for thread-safe log updates
    log_message = pyqtSignal(str)

    # Signal emitted when profile is saved (for hot reload)
    profile_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")

        # Settings for persistent window geometry
        self.settings = QSettings("d4lf", "MainWindow")

        self.setWindowTitle("D4LF")
        self.setMinimumSize(800, 600)

        # Restore window geometry
        self.resize(self.settings.value("size", QSize(800, 600)))
        self.move(self.settings.value("pos", QPoint(100, 100)))

        if self.settings.value("maximized", "false") == "true":
            self.showMaximized()

        # Set window icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # References to child windows (so they don't get garbage collected)
        self.settings_window = None
        self.editor_window = None
        self.import_window = None

        # Apply theme based on settings
        self.apply_current_theme()

        # Setup UI
        self.setup_ui()

        # Connect log handler to capture d4lf output
        self.setup_logging()

    def apply_current_theme(self):
        try:
            config = IniConfigLoader()
            theme_enum = config.general.theme

            # FIX: use .value to get the actual string
            theme_mode = theme_enum.value.lower()

            stylesheet = LIGHT_THEME if theme_mode == "light" else DARK_THEME

            QApplication.instance().setStyleSheet(stylesheet)

        except Exception as e:
            LOGGER.warning(f"Could not load theme setting, using dark theme: {e}")
            QApplication.instance().setStyleSheet(DARK_THEME)

    def setup_ui(self):
        """Create the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === VERSION HEADER ===
        version_label = QLabel(f"D4LF - Diablo 4 Loot Filter v{__version__}")
        version_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(version_label)

        # === LOG VIEWER (Top - Scrollable) ===
        log_label = QLabel("Activity Log:")
        log_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(log_label)

        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumBlockCount(1000)  # Limit to last 1000 lines
        self.log_viewer.setPlaceholderText("Waiting for d4lf to start scanning...")

        # Add some initial welcome message
        self.log_viewer.appendPlainText("═" * 80)
        self.log_viewer.appendPlainText("D4LF - Diablo 4 Loot Filter")
        self.log_viewer.appendPlainText("═" * 80)
        self.log_viewer.appendPlainText("")

        main_layout.addWidget(self.log_viewer, stretch=1)

        # === HOTKEYS PANEL (Compact 2-line) ===
        hotkeys_label = QLabel("Hotkeys:")
        hotkeys_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(hotkeys_label)

        # Build hotkey display from config
        config = IniConfigLoader()

        # Create a formatted text block
        hotkey_text = QLabel()
        hotkey_text.setMaximumHeight(65)
        hotkey_text.setWordWrap(True)
        hotkey_text.setTextFormat(Qt.TextFormat.RichText)
        hotkey_text.setStyleSheet("margin-left: 5px;")

        hotkeys_html = "<div style='font-size: 9pt; line-height: 1.5; font-weight: normal;'>"

        if not config.advanced_options.vision_mode_only:
            # Line 1: Main hotkeys
            hotkeys_html += f"<u><b>{config.advanced_options.run_vision_mode.upper()}</b></u>: Run/Stop Vision Mode&nbsp;&nbsp;&nbsp;"
            hotkeys_html += (
                f"<u><b>{config.advanced_options.run_filter.upper()}</b></u>: Run/Stop Auto Filter&nbsp;&nbsp;&nbsp;"
            )
            hotkeys_html += (
                f"<u><b>{config.advanced_options.move_to_inv.upper()}</b></u>: Move Chest → Inventory&nbsp;&nbsp;&nbsp;"
            )
            hotkeys_html += f"<u><b>{config.advanced_options.move_to_chest.upper()}</b></u>: Move Inventory → Chest<br>"

            # Line 2: Secondary hotkeys
            hotkeys_html += f"<u><b>{config.advanced_options.run_filter_force_refresh.upper()}</b></u>: Force Filter (Reset Item Status)&nbsp;&nbsp;&nbsp;"
            hotkeys_html += f"<u><b>{config.advanced_options.force_refresh_only.upper()}</b></u>: Reset Items (No Filter)&nbsp;&nbsp;&nbsp;"
        else:
            hotkeys_html += f"<u><b>{config.advanced_options.run_vision_mode.upper()}</b></u>: Run/Stop Vision Mode<br>"
            hotkeys_html += "<span style='font-style: italic;'>Vision Mode Only - clicking functionality disabled</span>&nbsp;&nbsp;&nbsp;"

        hotkeys_html += f"<u><b>{config.advanced_options.exit_key.upper()}</b></u>: Exit D4LF"
        hotkeys_html += "</div>"

        hotkey_text.setText(hotkeys_html)
        main_layout.addWidget(hotkey_text)

        # === CONTROL BUTTONS (Bottom) ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Import Profile Button
        self.import_btn = QPushButton("Import Profile")
        self.import_btn.setMinimumHeight(40)
        self.import_btn.clicked.connect(self.open_import_dialog)
        button_layout.addWidget(self.import_btn)

        # Settings Button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setMinimumHeight(40)
        self.settings_btn.clicked.connect(self.open_settings)
        button_layout.addWidget(self.settings_btn)

        # Profile Editor Button
        self.editor_btn = QPushButton("Edit Profile")
        self.editor_btn.setMinimumHeight(40)
        self.editor_btn.clicked.connect(self.open_profile_editor)
        button_layout.addWidget(self.editor_btn)

        main_layout.addLayout(button_layout)

        # Connect log signal to append method (thread-safe)
        self.log_message.connect(self.append_log)

    def setup_logging(self):
        """Setup log file monitoring."""
        # Find the most recent log file in the logs directory
        logs_dir = LOG_DIR

        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)

        # Find the most recent .txt log file
        log_files = list(logs_dir.glob("log_*.txt"))

        if log_files:
            # Get the most recently modified log file
            self.log_file_path = max(log_files, key=lambda p: p.stat().st_mtime)
        else:
            # No log file yet, create a placeholder path
            self.log_file_path = logs_dir / "d4lf.log"

        # Read all existing content first
        if self.log_file_path.exists():
            try:
                with Path(self.log_file_path).open(encoding="utf-8", errors="ignore") as f:
                    existing_content = f.read()
                    for line in existing_content.splitlines():
                        if line.strip():  # Skip empty lines
                            self.append_log(line)
                    self.log_file_position = f.tell()
            except Exception as e:
                print(f"DEBUG: Error reading existing log content: {e}")
                self.log_file_position = 0
        else:
            self.log_file_position = 0

        # Start timer to check log file for new content
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.read_log_file)
        self.log_timer.start(500)  # Check every 500ms

        LOGGER.info("Main window initialized")

    def read_log_file(self):
        """Read new lines from log file."""
        try:
            # Check if a newer log file exists
            logs_dir = LOG_DIR
            log_files = list(logs_dir.glob("log_*.txt"))
            if log_files:
                newest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                if newest_log != self.log_file_path:
                    # Switch to the new log file
                    self.log_file_path = newest_log
                    self.log_file_position = 0
                    print(f"DEBUG: Switched to new log file: {self.log_file_path}")

            if not self.log_file_path.exists():
                return

            # Check if file has grown
            current_size = self.log_file_path.stat().st_size
            if current_size <= self.log_file_position:
                return  # No new data

            with Path(self.log_file_path).open(encoding="utf-8", errors="ignore") as f:
                f.seek(self.log_file_position)
                new_lines = f.readlines()
                self.log_file_position = f.tell()

                for line in new_lines:
                    # Remove trailing newline and add to log viewer
                    self.append_log(line.rstrip())

        except Exception as e:
            # File might be locked, try again next time
            LOGGER.debug(f"Error reading log file: {e}")

    def append_log(self, message):
        """Append message to log viewer (thread-safe slot)."""
        parts = message.split(" | ", 5)
        if len(parts) >= 5:
            actual_message = parts[5] if len(parts) == 6 else parts[4]

            # Check for [CLEAN] marker - show only pipe without level
            if actual_message.startswith("[CLEAN]"):
                clean_message = "| " + actual_message[7:]  # Remove [CLEAN] marker
            else:
                level = parts[3]
                clean_message = actual_message if level == "INFO" else f"{level} | {actual_message}"
        else:
            clean_message = message

        self.log_viewer.appendPlainText(clean_message)
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def open_import_dialog(self):
        """Open maxroll/d4builds/mobalytics importer."""
        LOGGER.info("Opening profile importer...")

        try:
            if self.import_window is None or not self.import_window.isVisible():
                self.import_window = ImporterWindow(self)
                self.import_window.show()
            else:
                self.import_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open importer: {e}")
            QMessageBox.critical(self, "Import Error", str(e))

    def open_settings(self):
        """Open settings/config window."""
        LOGGER.info("Opening settings window...")

        try:
            if self.settings_window is None or not self.settings_window.isVisible():
                # Pass the theme reload callback
                self.settings_window = ConfigWindow(self, theme_changed_callback=self.on_settings_changed)
                self.settings_window.show()
            else:
                # Window already open - bring to front
                self.settings_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open settings: {e}")
            QMessageBox.critical(self, "Settings Error", str(e))

    def open_profile_editor(self):
        """Open profile editor window."""
        LOGGER.info("Opening profile editor...")

        try:
            if self.editor_window is None or not self.editor_window.isVisible():
                self.editor_window = ProfileEditorWindow(self)
                self.editor_window.destroyed.connect(lambda: setattr(self, "editor_window", None))
                self.editor_window.show()
            else:
                self.editor_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open profile editor: {e}")
            QMessageBox.critical(self, "Editor Error", str(e))

    def on_settings_changed(self):
        LOGGER.info("Settings changed - reloading theme...")

        app = QApplication.instance()

        # Pause Profile Editor updates
        if self.editor_window and self.editor_window.isVisible():
            self.editor_window._ignore_theme_updates = True

        # Apply the theme globally
        self.apply_current_theme()

        # Force Qt to re-polish the entire application
        app.style().unpolish(app)
        app.style().polish(app)

        # Resume Profile Editor updates
        if self.editor_window and self.editor_window.isVisible():
            QTimer.singleShot(0, lambda: setattr(self.editor_window, "_ignore_theme_updates", False))

    def closeEvent(self, event):
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.close()

        if self.editor_window and self.editor_window.isVisible():
            self.editor_window.close()

        if self.import_window and self.import_window.isVisible():
            self.import_window.close()

        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", "true" if self.isMaximized() else "false")

        shutdown_flag = BASE_DIR / "assets" / ".shutdown"
        shutdown_flag.touch()

        event.accept()


# Example usage for testing
if __name__ == "__main__":
    import sys

    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    # Simulate some log messages
    LOGGER.info("d4lf starting...")
    LOGGER.info("Loading profiles...")
    LOGGER.info("Starting item scanner...")
    LOGGER.info("Ready to scan!")

    sys.exit(app.exec())
