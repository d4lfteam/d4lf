"""
Main Window for d4lf - integrates scanning overlay with GUI controls.
Shows log output and provides access to Import, Settings, and Profile Editor.
"""

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from src.gui.themes import DARK_THEME, LIGHT_THEME
from src.config.loader import IniConfigLoader
from src.logger import LOG_DIR

LOGGER = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Custom logging handler that emits log records to Qt signal"""
    
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        
    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class MainWindow(QMainWindow):
    """
    Main window that houses:
    - Top: Real-time log viewer showing d4lf scanning output
    - Bottom: Three buttons for Import Profile, Settings, and Edit Profile
    """
    
    # Signal for thread-safe log updates
    log_message = pyqtSignal(str)
    
    # Signal emitted when profile is saved (for hot reload)
    profile_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("d4lf - Loot Filter")
        self.setMinimumSize(800, 600)
        
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
        """Apply the theme from settings (dark or light)"""
        try:
            # Load current theme setting
            config = IniConfigLoader()
            theme_mode = config.general.theme  # Assuming this is how you store it
            
            if theme_mode.lower() == "light":
                self.setStyleSheet(LIGHT_THEME)
            else:
                self.setStyleSheet(DARK_THEME)
                
        except Exception as e:
            # Default to dark theme if settings can't be loaded
            LOGGER.warning(f"Could not load theme setting, using dark theme: {e}")
            self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        """Create the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === VERSION HEADER ===
        from src import __version__
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
        self.log_viewer.appendPlainText("d4lf - Diablo 4 Loot Filter")
        self.log_viewer.appendPlainText("═" * 80)
        self.log_viewer.appendPlainText("")

        main_layout.addWidget(self.log_viewer, stretch=1)

        # === HOTKEYS PANEL (Fixed - doesn't scroll away) ===
        hotkeys_label = QLabel("Hotkeys:")
        hotkeys_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(hotkeys_label)

        # Create hotkeys table
        hotkeys_table = QTableWidget()
        hotkeys_table.setColumnCount(2)
        hotkeys_table.setHorizontalHeaderLabels(["Hotkey", "Action"])
        hotkeys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hotkeys_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hotkeys_table.verticalHeader().setVisible(False)
        hotkeys_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hotkeys_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Build hotkey data from config
        config = IniConfigLoader()
        hotkey_data = []

        if not config.advanced_options.vision_mode_only:
            hotkey_data.append((config.advanced_options.run_vision_mode, "Run/Stop Vision Mode"))
            hotkey_data.append((config.advanced_options.run_filter, "Run/Stop Auto Filter"))
            hotkey_data.append(
                (config.advanced_options.run_filter_force_refresh, "Force Run/Stop Filter (Reset Item Status)"))
            hotkey_data.append((config.advanced_options.force_refresh_only, "Reset Item Statuses Without Filter"))
            hotkey_data.append((config.advanced_options.move_to_inv, "Move Items: Chest → Inventory"))
            hotkey_data.append((config.advanced_options.move_to_chest, "Move Items: Inventory → Chest"))
        else:
            hotkey_data.append((config.advanced_options.run_vision_mode, "Run/Stop Vision Mode"))
            hotkey_data.append(("N/A", "Vision Mode Only - clicking disabled"))

        hotkey_data.append((config.advanced_options.exit_key, "Exit d4lf"))

        # Populate table
        hotkeys_table.setRowCount(len(hotkey_data))
        for row, (hotkey, action) in enumerate(hotkey_data):
            hotkeys_table.setItem(row, 0, QTableWidgetItem(hotkey))
            hotkeys_table.setItem(row, 1, QTableWidgetItem(action))

        # Set table to fit content exactly
        hotkeys_table.resizeRowsToContents()
        table_height = hotkeys_table.horizontalHeader().height() + 2  # header + borders
        for i in range(hotkeys_table.rowCount()):
            table_height += hotkeys_table.rowHeight(i)
        hotkeys_table.setMaximumHeight(table_height)
        hotkeys_table.setMinimumHeight(table_height)

        main_layout.addWidget(hotkeys_table)

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
        """Setup log file monitoring"""
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

        print(f"DEBUG: Log file path: {self.log_file_path}")
        print(f"DEBUG: Log file exists: {self.log_file_path.exists()}")

        # Read all existing content first
        if self.log_file_path.exists():
            try:
                with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
        """Read new lines from log file"""
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

            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.log_file_position)
                new_lines = f.readlines()
                self.log_file_position = f.tell()

                for line in new_lines:
                    # Remove trailing newline and add to log viewer
                    self.append_log(line.rstrip())

        except Exception as e:
            # File might be locked, try again next time
            pass

    def append_log(self, message):
        """Append message to log viewer (thread-safe slot)"""
        # Strip timestamp, thread, and source location from log messages
        # Format: "2025-12-31 | 07:16:43.047 | MainThread | INFO | src.item.filter:537 | actual message"
        # Keep only: "INFO | actual message" (or just "actual message" for INFO)

        parts = message.split(" | ", 5)  # Split into max 6 parts
        if len(parts) >= 5:
            # parts[0] = date, parts[1] = time, parts[2] = thread, parts[3] = level, parts[4] = source, parts[5] = message
            level = parts[3]  # INFO, ERROR, WARNING, etc.
            actual_message = parts[5] if len(parts) == 6 else parts[4]  # Message might be in parts[4] if no source

            # For INFO, just show the message. For errors/warnings, show level too
            if level == "INFO":
                clean_message = actual_message
            else:
                clean_message = f"{level} | {actual_message}"
        else:
            # If format doesn't match, show original
            clean_message = message

        self.log_viewer.appendPlainText(clean_message)

        # Auto-scroll to bottom
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def open_import_dialog(self):
        """Open maxroll/d4builds/mobalytics importer"""
        LOGGER.info("Opening profile importer...")

        try:
            from src.gui.importer_window import ImporterWindow

            if self.import_window is None or not self.import_window.isVisible():
                self.import_window = ImporterWindow()
                self.import_window.show()
            else:
                self.import_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open importer: {e}")
            QMessageBox.critical(self, "Import Error", str(e))

    def open_settings(self):
        """Open settings/config window"""
        LOGGER.info("Opening settings window...")

        try:
            from src.gui.config_window import ConfigWindow

            if self.settings_window is None or not self.settings_window.isVisible():
                # Pass the theme reload callback
                self.settings_window = ConfigWindow(theme_changed_callback=self.on_settings_changed)
                self.settings_window.show()
            else:
                # Window already open - bring to front
                self.settings_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open settings: {e}")
            QMessageBox.critical(self, "Settings Error", str(e))

    def open_profile_editor(self):
        """Open profile editor window"""
        LOGGER.info("Opening profile editor...")

        try:
            from src.gui.profile_editor_window import ProfileEditorWindow

            if self.editor_window is None or not self.editor_window.isVisible():
                self.editor_window = ProfileEditorWindow()
                self.editor_window.show()
            else:
                self.editor_window.activateWindow()

        except Exception as e:
            LOGGER.error(f"Failed to open profile editor: {e}")
            QMessageBox.critical(self, "Editor Error", str(e))

    def on_profile_saved(self, profile_name):
        """
        Called when profile is saved in Profile Editor.
        Triggers hot reload of filters without restarting.
        """
        LOGGER.info(f"Profile '{profile_name}' saved - triggering reload...")

        try:
            # Reload the profile configuration
            from src.config.loader import ProfileLoader
            ProfileLoader.reload_profile(profile_name)

            # Reload item filters
            from src.item.filter import Filter
            Filter.reload()  # or whatever your reload mechanism is

            self.profile_updated.emit(profile_name)

            LOGGER.info(f"✓ Profile '{profile_name}' reloaded successfully")

        except Exception as e:
            LOGGER.error(f"Failed to reload profile: {e}")
            QMessageBox.warning(
                self,
                "Reload Failed",
                f"Profile saved but reload failed:\n{str(e)}\n\nPlease restart d4lf."
            )
    
    def on_settings_changed(self):
        """
        Called when settings are changed (e.g., theme switch).
        Reloads the theme without restarting.
        """
        LOGGER.info("Settings changed - reloading theme...")
        self.apply_current_theme()
        
        # Also update child windows if they're open
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.setStyleSheet(self.styleSheet())
        if self.editor_window and self.editor_window.isVisible():
            self.editor_window.setStyleSheet(self.styleSheet())


# Example usage for testing
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
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
