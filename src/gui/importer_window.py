import logging
import threading

from PyQt6.QtCore import QObject, QPoint, QRunnable, QSettings, QSize, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.gui.importer.d4builds import import_d4builds
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import import_maxroll
from src.gui.importer.mobalytics import import_mobalytics
from src.gui.open_user_config_button import OpenUserConfigButton
from src.gui.themes import DARK_THEME, LIGHT_THEME

LOGGER = logging.getLogger(__name__)
THREADPOOL = QThreadPool()


class ImporterWindow(QMainWindow):
    """Standalone window for Maxroll/D4Builds/Mobalytics importer"""

    def __init__(self):
        super().__init__()

        # Settings for persistent window geometry
        self.settings = QSettings("d4lf", "ImporterWindow")

        self.setWindowTitle("Profile Importer - Maxroll / D4Builds / Mobalytics")
        self.setMinimumSize(700, 600)

        # Restore window geometry
        self.resize(self.settings.value("size", QSize(700, 600)))
        self.move(self.settings.value("pos", QPoint(100, 100)))

        if self.settings.value("maximized", "false") == "true":
            self.showMaximized()

        # Apply theme
        self._apply_theme()

        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # URL input
        url_hbox = QHBoxLayout()
        url_label = QLabel("URL:")
        url_hbox.addWidget(url_label)
        self.input_box = QLineEdit()
        self.input_box.textChanged.connect(self._handle_text_changed)
        url_hbox.addWidget(self.input_box)
        layout.addLayout(url_hbox)

        # Filename input
        filename_hbox = QHBoxLayout()
        filename_label = QLabel("Custom file name:")
        filename_hbox.addWidget(filename_label)
        self.filename_input_box = QLineEdit()
        self.filename_input_box.setPlaceholderText("Leave blank for default filename")
        filename_hbox.addWidget(self.filename_input_box)
        layout.addLayout(filename_hbox)

        # Checkboxes
        checkbox_hbox = QHBoxLayout()
        self.import_uniques_checkbox = QCheckBox("Import Uniques")
        self.import_uniques_checkbox.setChecked(True)
        self.import_uniques_checkbox.setToolTip(
            "Should uniques be included in the profile if they exist on the build page?"
        )

        self.import_aspect_upgrades_checkbox = QCheckBox("Import Aspect Upgrades")
        self.import_aspect_upgrades_checkbox.setChecked(True)
        self.import_aspect_upgrades_checkbox.setToolTip(
            "If legendary aspects are in the build, do you want an aspect upgrades section generated for them?"
        )

        self.add_to_profiles_checkbox = QCheckBox("Auto-add To Profiles")
        self.add_to_profiles_checkbox.setChecked(True)
        self.add_to_profiles_checkbox.setToolTip(
            "After import, should the imported file be automatically added to your active profiles?"
        )

        checkbox_hbox.addWidget(self.import_uniques_checkbox)
        checkbox_hbox.addWidget(self.import_aspect_upgrades_checkbox)
        checkbox_hbox.addWidget(self.add_to_profiles_checkbox)
        layout.addLayout(checkbox_hbox)

        # Generate button
        button_hbox = QHBoxLayout()
        self.generate_button = QPushButton("Generate")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate_button_click)
        button_hbox.addWidget(self.generate_button)

        profiles_button = OpenUserConfigButton()
        button_hbox.addWidget(profiles_button)
        layout.addLayout(button_hbox)

        # Log output
        log_label = QLabel("Log:")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Setup logging
        self.log_handler = _GuiLogHandler(self.log_output)
        LOGGER.root.addHandler(self.log_handler)

        # Instructions
        instructions_label = QLabel("Instructions:")
        layout.addWidget(instructions_label)

        instructions_text = QTextEdit()
        instructions_text.setText(
            "You can link either the build guide or a direct link to the specific planner.\n\n"
            "https://maxroll.gg/d4/build-guides/tornado-druid-guide\n"
            "or\n"
            "https://maxroll.gg/d4/planner/cm6pf0xa#5\n"
            "or\n"
            "https://d4builds.gg/builds/ef414fbd-81cd-49d1-9c8d-4938b278e2ee\n"
            "or\n"
            "https://mobalytics.gg/diablo-4/builds/barbarian/bash\n\n"
            f"It will create a file based on the label of the build in the planner in: {IniConfigLoader().user_dir / 'profiles'}\n\n"
            "For d4builds you need to specify your browser in the config tab"
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

    def _apply_theme(self):
        """Apply theme from settings"""
        config = IniConfigLoader()
        theme = config.general.theme.value
        if theme == "dark":
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)

    def _handle_text_changed(self, text):
        """Enable/disable generate button based on input"""
        self.generate_button.setEnabled(bool(text.strip()))

    def _generate_button_click(self):
        """Handle generate button click"""
        url = self.input_box.text().strip()
        custom_filename = self.filename_input_box.text()
        if custom_filename:
            custom_filename = custom_filename.split(".")[0]
            custom_filename = custom_filename.strip()

        importer_config = ImportConfig(
            url,
            self.import_uniques_checkbox.isChecked(),
            self.import_aspect_upgrades_checkbox.isChecked(),
            self.add_to_profiles_checkbox.isChecked(),
            custom_filename,
        )

        if "maxroll" in url:
            worker = _Worker(name="maxroll", fn=import_maxroll, config=importer_config)
        elif "d4builds" in url:
            worker = _Worker(name="d4builds", fn=import_d4builds, config=importer_config)
        else:
            worker = _Worker(name="mobalytics", fn=import_mobalytics, config=importer_config)

        worker.signals.finished.connect(self._on_worker_finished)
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating...")
        THREADPOOL.start(worker)

    def _on_worker_finished(self):
        """Handle worker completion"""
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate")
        self.filename_input_box.clear()

    def closeEvent(self, event):
        """Cleanup when window closes and save geometry"""
        # Save window geometry
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", "true" if self.isMaximized() else "false")

        # Cleanup log handler
        LOGGER.root.removeHandler(self.log_handler)
        event.accept()


class _GuiLogHandler(logging.Handler):
    """Thread-safe log handler that emits signals for GUI updates"""

    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self.text_widget = text_widget
        self.signals = _LogSignals()
        # Connect signal to slot in main thread
        self.signals.log_message.connect(self._append_log)
        # Set log level to DEBUG to capture everything
        self.setLevel(logging.DEBUG)

    def emit(self, record):
        """Called from any thread - emit signal instead of direct GUI update"""
        try:
            log_entry = self.format(record)
            self.signals.log_message.emit(log_entry)
        except Exception:
            self.handleError(record)

    def _append_log(self, message):
        """Slot that runs in main thread - safe to update GUI"""
        self.text_widget.append(message)
        self.text_widget.ensureCursorVisible()


class _LogSignals(QObject):
    """Signals for thread-safe logging"""

    log_message = pyqtSignal(str)


class _Worker(QRunnable):
    def __init__(self, name, fn, *args, **kwargs):
        super().__init__()
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _WorkerSignals()

    @pyqtSlot()
    def run(self):
        threading.current_thread().name = self.name
        self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit()


class _WorkerSignals(QObject):
    finished = pyqtSignal()
