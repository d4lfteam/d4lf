import logging
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QRunnable, QSettings, QSize, Qt, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.gui.importer.d4builds import import_d4builds
from src.gui.importer.importer_config import DEFAULT_FILENAME_PARTS, FilenamePart, ImportConfig
from src.gui.importer.maxroll import import_maxroll
from src.gui.importer.mobalytics import import_mobalytics
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)
THREADPOOL = QThreadPool()
FILENAME_PART_LABELS = {
    FilenamePart.SOURCE: "Source",
    FilenamePart.SEASON: "Season",
    FilenamePart.CLASS: "Class",
    FilenamePart.BUILD_TITLE: "Build title",
    FilenamePart.VARIANT: "Variant",
}
GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP = "Select at least one filename part or enter a custom file name."


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
        self.is_generating = False

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
        self.input_box.textChanged.connect(self._update_generate_button_state)
        url_hbox.addWidget(self.input_box)
        self.generate_button = QPushButton("Generate")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate_button_click)
        url_hbox.addWidget(self.generate_button)
        layout.addLayout(url_hbox)

        # Filename input
        filename_hbox = QHBoxLayout()
        filename_label = QLabel("Custom file name:")
        filename_hbox.addWidget(filename_label)
        self.filename_input_box = QLineEdit()
        self.filename_input_box.setPlaceholderText("Leave blank for default filename")
        self.filename_input_box.textChanged.connect(self._update_generate_button_state)
        filename_hbox.addWidget(self.filename_input_box)
        self.filename_parts_button = QPushButton("Default filename includes...")
        self.filename_parts_menu = QMenu(self.filename_parts_button)
        self.filename_part_actions: dict[FilenamePart, QAction] = {}
        for filename_part in DEFAULT_FILENAME_PARTS:
            action = QAction(FILENAME_PART_LABELS[filename_part], self.filename_parts_menu)
            action.setCheckable(True)
            action.setChecked(self._filename_part_setting(filename_part))
            action.toggled.connect(
                lambda checked, part=filename_part: self._handle_filename_part_toggled(part, checked)
            )
            self.filename_parts_menu.addAction(action)
            self.filename_part_actions[filename_part] = action
        self.filename_parts_button.setMenu(self.filename_parts_menu)
        filename_hbox.addWidget(self.filename_parts_button)
        layout.addLayout(filename_hbox)

        self.filename_parts_summary_label = QLabel()
        layout.addWidget(self.filename_parts_summary_label)
        self._update_filename_parts_summary()
        self._update_generate_button_state()

        # Checkboxes
        self.import_aspect_upgrades_checkbox = self._generate_checkbox(
            "Import Aspect Upgrades",
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
            "Import Paragon",
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

        # Use a grid layout to ensure checkboxes align vertically in columns
        checkbox_grid = QGridLayout()
        checkbox_grid.setContentsMargins(0, 10, 0, 10)
        checkbox_grid.setSpacing(10)

        checkbox_grid.addWidget(self.import_aspect_upgrades_checkbox, 0, 0)
        checkbox_grid.addWidget(self.import_gas_checkbox, 0, 1)
        checkbox_grid.addWidget(self.require_all_gas_checkbox, 0, 2)

        checkbox_grid.addWidget(self.export_paragon_checkbox, 1, 0)
        checkbox_grid.addWidget(self.add_to_profiles_checkbox, 1, 1)

        layout.addLayout(checkbox_grid)

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

    def _filename_part_setting(self, filename_part: FilenamePart) -> bool:
        value = self.settings.value(self._filename_part_setting_key(filename_part), "true")
        return value is True or str(value).casefold() == "true"

    def _handle_filename_part_toggled(self, filename_part: FilenamePart, checked: bool):
        self.settings.setValue(self._filename_part_setting_key(filename_part), checked)
        self._update_filename_parts_summary()
        self._update_generate_button_state()

    def _selected_filename_parts(self) -> tuple[FilenamePart, ...]:
        return tuple(part for part in DEFAULT_FILENAME_PARTS if self.filename_part_actions[part].isChecked())

    def _update_filename_parts_summary(self):
        selected_labels = [FILENAME_PART_LABELS[part] for part in self._selected_filename_parts()]
        summary = "_".join(selected_labels) + ".yaml" if selected_labels else "none"
        self.filename_parts_summary_label.setText(f"Default file name: {summary}")

    def _update_generate_button_state(self):
        if self.is_generating:
            self.generate_button.setEnabled(False)
            return
        url_ready = bool(self.input_box.text().strip())
        filename_ready = bool(self.filename_input_box.text().strip()) or bool(self._selected_filename_parts())
        self.generate_button.setEnabled(url_ready and filename_ready)
        if url_ready and not filename_ready:
            self.generate_button.setToolTip(GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP)
        elif not url_ready:
            self.generate_button.setToolTip("Enter a URL to generate a profile.")
        else:
            self.generate_button.setToolTip("")

    def _generate_button_click(self):
        """Handle generate button click."""
        if not self.generate_button.isEnabled():
            return
        self.log_output.clear()
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
            self._selected_filename_parts(),
        )

        if "maxroll" in url:
            worker = _Worker(name="maxroll", fn=import_maxroll, config=importer_config)
        elif "d4builds" in url:
            worker = _Worker(name="d4builds", fn=import_d4builds, config=importer_config)
        else:
            worker = _Worker(name="mobalytics", fn=import_mobalytics, config=importer_config)

        worker.signals.finished.connect(self._on_worker_finished)
        self.is_generating = True
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating...")
        THREADPOOL.start(worker)

    def _on_worker_finished(self):
        """Handle worker completion."""
        self.is_generating = False
        self.generate_button.setText("Generate")
        self.filename_input_box.clear()
        self._update_generate_button_state()
        self.import_completed.emit()

    @staticmethod
    def _filename_part_setting_key(filename_part: FilenamePart) -> str:
        return f"filename_part_{filename_part.value}"

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
        logging.getLogger("src.gui.importer.gui_common").removeHandler(self.log_handler)
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
