import logging
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QRunnable, QSettings, QSize, Qt, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.config.loader import IniConfigLoader
from src.gui.importer.d4builds import import_d4builds
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import import_maxroll
from src.gui.importer.mobalytics import import_mobalytics
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)
THREADPOOL = QThreadPool()


class ImporterWindow(QMainWindow):
    """Standalone window for Maxroll/D4Builds/Mobalytics importer."""

    import_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Settings for persistent window geometry
        self.settings = QSettings("d4lf", "ImporterWindow")

        self.setWindowTitle("Profile Importer - Maxroll / D4Builds / Mobalytics")
        self.setMinimumSize(700, 600)

        # Restore window geometry
        self.resize(self.settings.value("size", QSize(700, 600)))
        self.move(self.settings.value("pos", QPoint(100, 100)))

        if self.settings.value("maximized", "false") == "true":
            self.showMaximized()

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

        # Filename input with inline filename options row
        self.filename_input_box = QLineEdit()
        self.filename_input_box.setPlaceholderText("Leave blank for default filename")

        self.filename_label = QLabel("Custom file name:")
        self.filename_label_layout = QHBoxLayout()
        self.filename_label_layout.addWidget(self.filename_label)
        self.filename_label_layout.addWidget(self.filename_input_box)

        # Filename Options label and checkboxes in a single row
        self.filename_options_label = QLabel("Filename Options:")
        self.filename_options_label.setFixedWidth(120)

        self.include_source_checkbox = CheckmarkCheckBox("Source")
        self.include_source_checkbox.setToolTip("Include the build source (e.g., maxroll, d4builds, mobalytics)")
        self.include_source_checkbox.setChecked(True)

        self.include_season_checkbox = CheckmarkCheckBox("Season")
        self.include_season_checkbox.setToolTip("Include the season number (e.g., s5)")
        self.include_season_checkbox.setChecked(True)

        self.include_class_checkbox = CheckmarkCheckBox("Class")
        self.include_class_checkbox.setToolTip("Include the character class (e.g., Barbarian, Druid)")
        self.include_class_checkbox.setChecked(True)

        self.include_header_checkbox = CheckmarkCheckBox("Build Name")
        self.include_header_checkbox.setToolTip("Include the main build name/guide title")
        self.include_header_checkbox.setChecked(True)

        self.include_subbuild_checkbox = CheckmarkCheckBox("Sub Build")
        self.include_subbuild_checkbox.setToolTip("Include the sub-build/variant name")
        self.include_subbuild_checkbox.setChecked(True)

        self.filename_options_hbox = QHBoxLayout()
        self.filename_options_hbox.addWidget(self.filename_options_label)
        self.filename_options_hbox.addWidget(self.include_source_checkbox)
        self.filename_options_hbox.addWidget(self.include_season_checkbox)
        self.filename_options_hbox.addWidget(self.include_class_checkbox)
        self.filename_options_hbox.addWidget(self.include_header_checkbox)
        self.filename_options_hbox.addWidget(self.include_subbuild_checkbox)
        self.filename_options_hbox.addStretch()

        layout.addLayout(self.filename_label_layout)
        layout.addLayout(self.filename_options_hbox)

        # Generate button
        button_hbox = QHBoxLayout()
        self.generate_button = QPushButton("Generate")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate_button_click)
        button_hbox.addWidget(self.generate_button)
        layout.addLayout(button_hbox)

        # Import Options label and checkboxes in a single row
        self.import_options_label = QLabel("Import Options:")
        self.import_options_label.setFixedWidth(120)

        self.import_aspect_upgrades_checkbox = self._generate_checkbox(
            "Aspect Upgrades",
            "import_aspect_upgrades",
            "If legendary aspects are in the build, do you want an aspect upgrades section generated for them?",
        )
        self.add_to_profiles_checkbox = self._generate_checkbox(
            "Auto-add To Profiles",
            "import_add_to_profiles",
            "After import, should the imported file be automatically added to your active profiles?",
        )
        self.import_gas_checkbox = self._generate_checkbox(
            "Import GAs",
            "import_gas",
            "If a build has greater affixes, should they be included in the imported profile?",
        )
        self.require_all_gas_checkbox = self._generate_checkbox(
            "Require all GAs",
            "require_all_gas",
            "If a build has greater affixes, should an item have all of them to be kept?",
            "false",
        )

        self.export_paragon_checkbox = self._generate_checkbox(
            "Paragon",
            "export_paragon",
            "Import Paragon boards into your profile for the integrated Paragon overlay.",
            "false",
        )

        # GA dependency logic
        def disable_require_if_import_disabled():
            if not self.import_gas_checkbox.isChecked():
                self.require_all_gas_checkbox.setChecked(False)
                self.require_all_gas_checkbox.setEnabled(False)
            else:
                self.require_all_gas_checkbox.setEnabled(True)

        # Apply initial enabled/disabled state
        self.require_all_gas_checkbox.setEnabled(self.import_gas_checkbox.isChecked())

        # Apply initial gray-out if Import GAs starts off
        if not self.import_gas_checkbox.isChecked():
            self.require_all_gas_checkbox.setChecked(False)
            self.require_all_gas_checkbox.setEnabled(False)

        # Connect toggle logic
        self.import_gas_checkbox.stateChanged.connect(lambda: disable_require_if_import_disabled())

        self.import_options_hbox = QHBoxLayout()
        self.import_options_hbox.addWidget(self.import_options_label)
        self.import_options_hbox.addWidget(self.import_aspect_upgrades_checkbox)
        self.import_options_hbox.addWidget(self.add_to_profiles_checkbox)
        self.import_options_hbox.addWidget(self.import_gas_checkbox)
        self.import_options_hbox.addWidget(self.require_all_gas_checkbox)
        self.import_options_hbox.addWidget(self.export_paragon_checkbox)
        self.import_options_hbox.addStretch()

        layout.addLayout(self.import_options_hbox)

        # Log output
        log_label = QLabel("Log:")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Setup logging
        self.log_handler = _GuiLogHandler(self.log_output)

        # Attach directly to each importer logger AND gui_common.py
        for name in (
            "src.gui.importer.mobalytics",
            "src.gui.importer.maxroll",
            "src.gui.importer.d4builds",
            "src.gui.importer.gui_common",
        ):
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(self.log_handler)

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
            "For d4builds you need to specify your browser in the Settings window"
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

    def _generate_checkbox(self, name, settings_value, desc, default_value="true") -> CheckmarkCheckBox:
        def save_setting_change(settings_value, value):
            self.settings.setValue(settings_value, value)

        checkbox = CheckmarkCheckBox(name)
        checkbox.setChecked(self.settings.value(settings_value, default_value) == "true")
        checkbox.setToolTip(desc)
        checkbox.stateChanged.connect(lambda: save_setting_change(settings_value, checkbox.isChecked()))
        return checkbox

    def _handle_text_changed(self, text):
        """Enable/disable generate button based on input."""
        self.generate_button.setEnabled(bool(text.strip()))
        # Show/hide filename options based on whether a custom filename is entered
        self.filename_options_label.setVisible(not bool(text.strip()))
        self.include_source_checkbox.setVisible(not bool(text.strip()))
        self.include_season_checkbox.setVisible(not bool(text.strip()))
        self.include_class_checkbox.setVisible(not bool(text.strip()))
        self.include_header_checkbox.setVisible(not bool(text.strip()))
        self.include_subbuild_checkbox.setVisible(not bool(text.strip()))

    def _get_filename_components(self) -> dict:
        """Build and return the filename_components dict from checkbox states."""
        return {
            "include_source": self.include_source_checkbox.isChecked(),
            "include_season": self.include_season_checkbox.isChecked(),
            "include_class": self.include_class_checkbox.isChecked(),
            "include_header": self.include_header_checkbox.isChecked(),
            "include_subbuild": self.include_subbuild_checkbox.isChecked(),
        }

    def _generate_button_click(self):
        self.log_output.clear()
        """Handle generate button click"""
        url = self.input_box.text().strip()
        custom_filename = self.filename_input_box.text()
        if custom_filename:
            custom_filename = custom_filename.split(".")[0]
            custom_filename = custom_filename.strip()

        importer_config = ImportConfig(
            url,
            self.import_aspect_upgrades_checkbox.isChecked(),
            self.add_to_profiles_checkbox.isChecked(),
            self.import_gas_checkbox.isChecked(),
            self.require_all_gas_checkbox.isChecked(),
            self.export_paragon_checkbox.isChecked(),
            custom_filename,
            self._get_filename_components() if not custom_filename else None,
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
        """Handle worker completion."""
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate")
        self.filename_input_box.clear()
        self.import_completed.emit()

    def closeEvent(self, event):  # noqa: N802
        """Cleanup when window closes and save geometry."""
        # Save window geometry
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", "true" if self.isMaximized() else "false")

        # Cleanup log handler
        logging.getLogger("src.gui.importer.mobalytics").removeHandler(self.log_handler)
        logging.getLogger("src.gui.importer.maxroll").removeHandler(self.log_handler)
        logging.getLogger("src.gui.importer.d4builds").removeHandler(self.log_handler)
        logging.getLogger("src.gui.importer.common").removeHandler(self.log_handler)
        event.accept()


class _GuiLogHandler(logging.Handler):
    """Thread-safe log handler that emits signals for GUI updates."""

    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self.text_widget = text_widget
        self.signals = _LogSignals()
        # Connect signal to slot in main thread
        self.signals.log_message.connect(self._append_log)
        # Set log level to DEBUG to capture everything
        self.setLevel(logging.DEBUG)

    def emit(self, record):
        """Called from any thread - emit signal instead of direct GUI update."""
        log_entry = self.format(record)
        try:
            self.signals.log_message.emit(log_entry)
        except RuntimeError:
            self.handleError(record)

    def _append_log(self, message):
        """Slot that runs in main thread - safe to update GUI."""
        try:
            self.text_widget.append(message)
            self.text_widget.ensureCursorVisible()
        except RuntimeError:
            # Handle the case where the widget was deleted while a signal was in flight
            pass


class _LogSignals(QObject):
    """Signals for thread-safe logging."""

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
