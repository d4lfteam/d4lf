import logging
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QRunnable, QSettings, QSize, Qt, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.gui.importer.d4builds import get_d4builds_variant_options, import_d4builds
from src.gui.importer.importer_config import ImportConfig, ImportVariantOption
from src.gui.importer.maxroll import get_maxroll_variant_options, import_maxroll
from src.gui.importer.mobalytics import get_mobalytics_variant_options, import_mobalytics
from src.gui.open_user_config_button import OpenUserConfigButton

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)
THREADPOOL = QThreadPool()
PROFILE_IMPORT_CANCELLED_MESSAGE = "Profile import cancelled"
PROFILE_IMPORT_CANCELLED_NO_VARIANT_SELECTED_MESSAGE = "Profile import cancelled, no variant selected"
VARIANT_DETECTION_MESSAGE = "Detecting variants, please wait..."
IMPORTER_LOGGER_NAMES = (
    "src.gui.importer_window",
    "src.gui.importer.mobalytics",
    "src.gui.importer.maxroll",
    "src.gui.importer.d4builds",
    "src.gui.importer.gui_common",
    "src.gui.importer.paragon_export",
)


def _get_importer_source_name(url: str) -> str:
    """Return a user-facing importer source name based on the URL."""
    lowered_url = url.casefold()
    if "d4builds" in lowered_url:
        return "D4Builds"
    if "maxroll" in lowered_url:
        return "Maxroll"
    return "Mobalytics"


def _build_variant_detection_log_message(url: str, variant_options: list[ImportVariantOption]) -> str:
    """Build a single importer log message describing the detected build variants."""
    source_name = _get_importer_source_name(url)
    variant_count = len(variant_options)
    plural_suffix = "s" if variant_count != 1 else ""
    return f"Discovered {variant_count} {source_name} variant{plural_suffix}."


@dataclass(frozen=True, slots=True)
class _PendingImportRequest:
    url: str
    custom_filename: str | None
    import_uniques: bool
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_all_gas: bool
    export_paragon: bool
    import_multiple_variants: bool


class _VariantSelectionDialog(QDialog):
    """Prompt for the build variants to import."""

    def __init__(self, variants: list[ImportVariantOption], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Variants")
        self.setMinimumSize(420, 360)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the variants to import."))

        self.variant_list = QListWidget(self)
        for variant in variants:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, variant.id)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.variant_list.addItem(item)
            checkbox = QCheckBox(variant.label, self.variant_list)
            checkbox.setChecked(True)
            item.setSizeHint(checkbox.sizeHint())
            self.variant_list.setItemWidget(item, checkbox)
        layout.addWidget(self.variant_list)

        button_row = QHBoxLayout()
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(lambda: self._set_all_checked(Qt.CheckState.Checked))
        button_row.addWidget(select_all_button)

        select_none_button = QPushButton("Select None")
        select_none_button.clicked.connect(lambda: self._set_all_checked(Qt.CheckState.Unchecked))
        button_row.addWidget(select_none_button)
        layout.addLayout(button_row)

        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(dialog_buttons)

    def _set_all_checked(self, state: Qt.CheckState) -> None:
        for index in range(self.variant_list.count()):
            checkbox = self._get_variant_checkbox(self.variant_list.item(index))
            if checkbox is not None:
                checkbox.setChecked(state == Qt.CheckState.Checked)

    def selected_variant_ids(self) -> tuple[str, ...]:
        selected_ids = []
        for index in range(self.variant_list.count()):
            item = self.variant_list.item(index)
            checkbox = self._get_variant_checkbox(item)
            if checkbox is not None and checkbox.isChecked():
                selected_ids.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return tuple(selected_ids)

    def _get_variant_checkbox(self, item: QListWidgetItem) -> QCheckBox | None:
        widget = self.variant_list.itemWidget(item)
        return widget if isinstance(widget, QCheckBox) else None


class ImporterWindow(QMainWindow):
    """Standalone window for Maxroll/D4Builds/Mobalytics importer."""

    def __init__(self, parent=None):
        super().__init__(parent)

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._pending_import_request: _PendingImportRequest | None = None

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

        # Filename input
        filename_hbox = QHBoxLayout()
        filename_label = QLabel("Custom file name:")
        filename_hbox.addWidget(filename_label)
        self.filename_input_box = QLineEdit()
        self.filename_input_box.setPlaceholderText("Leave blank for default filename")
        filename_hbox.addWidget(self.filename_input_box)
        layout.addLayout(filename_hbox)

        # Checkboxes
        self.import_uniques_checkbox = self._generate_checkbox(
            "Import Uniques",
            "import_uniques",
            "Should uniques be included in the profile if they exist on the build page?",
        )
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
        self.import_multiple_variants_checkbox = self._generate_checkbox(
            "Import Multiple Variants",
            "import_multiple_variants",
            "If enabled, detect all build variants and let you choose which ones to import. If disabled, only the current URL variant is imported.",
            "true",
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

        checkbox_hbox = QHBoxLayout()
        checkbox_hbox.addWidget(self.import_uniques_checkbox)
        checkbox_hbox.addWidget(self.import_aspect_upgrades_checkbox)
        checkbox_hbox.addWidget(self.add_to_profiles_checkbox)
        layout.addLayout(checkbox_hbox)
        # Second row of checkboxes, probably need a better solution for this one day
        checkbox_hbox = QHBoxLayout()
        checkbox_hbox.addWidget(self.import_gas_checkbox)
        checkbox_hbox.addWidget(self.require_all_gas_checkbox)
        checkbox_hbox.addWidget(self.export_paragon_checkbox)
        checkbox_hbox.addWidget(self.import_multiple_variants_checkbox)
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

        # Attach directly to each importer logger AND gui_common.py
        for name in IMPORTER_LOGGER_NAMES:
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

    def _generate_checkbox(self, name, settings_value, desc, default_value="true") -> QCheckBox:
        def save_setting_change(settings_value, value):
            self.settings.setValue(settings_value, value)

        checkbox = QCheckBox(name)
        checkbox.setChecked(self.settings.value(settings_value, default_value) == "true")
        checkbox.setToolTip(desc)
        checkbox.stateChanged.connect(lambda: save_setting_change(settings_value, checkbox.isChecked()))
        return checkbox

    def _handle_text_changed(self, text):
        """Enable/disable generate button based on input."""
        self.generate_button.setEnabled(bool(text.strip()))

    def _generate_button_click(self):
        self.log_output.clear()
        """Handle generate button click"""
        url = self.input_box.text().strip()
        custom_filename = self.filename_input_box.text()
        if custom_filename:
            custom_filename = custom_filename.split(".")[0]
            custom_filename = custom_filename.strip()

        request = _PendingImportRequest(
            url=url,
            custom_filename=custom_filename or None,
            import_uniques=self.import_uniques_checkbox.isChecked(),
            import_aspect_upgrades=self.import_aspect_upgrades_checkbox.isChecked(),
            add_to_profiles=self.add_to_profiles_checkbox.isChecked(),
            import_greater_affixes=self.import_gas_checkbox.isChecked(),
            require_all_gas=self.require_all_gas_checkbox.isChecked(),
            export_paragon=self.export_paragon_checkbox.isChecked(),
            import_multiple_variants=self.import_multiple_variants_checkbox.isChecked(),
        )

        if request.import_multiple_variants:
            self._pending_import_request = request
            self._set_generate_button_busy("Detecting...")
            LOGGER.info(VARIANT_DETECTION_MESSAGE)
            QApplication.processEvents()
            worker = _Worker(name="variant_detection", fn=self._get_variant_options_for_url, url=url)
            worker.signals.result.connect(self._on_variant_detection_result)
            worker.signals.error.connect(self._on_variant_detection_error)
            THREADPOOL.start(worker)
            return

        self._start_import_worker(request=request, selected_variants=())

    def _get_variant_options_for_url(self, url: str) -> list[ImportVariantOption]:
        if "maxroll" in url:
            return get_maxroll_variant_options(url)
        if "d4builds" in url:
            return get_d4builds_variant_options(url)
        return get_mobalytics_variant_options(url)

    def _build_import_config(
        self, request: _PendingImportRequest, selected_variants: tuple[str, ...] = ()
    ) -> ImportConfig:
        return ImportConfig(
            url=request.url,
            import_uniques=request.import_uniques,
            import_aspect_upgrades=request.import_aspect_upgrades,
            add_to_profiles=request.add_to_profiles,
            import_greater_affixes=request.import_greater_affixes,
            require_greater_affixes=request.require_all_gas,
            export_paragon=request.export_paragon,
            import_multiple_variants=request.import_multiple_variants,
            selected_variants=selected_variants,
            custom_file_name=request.custom_filename,
        )

    def _start_import_worker(self, request: _PendingImportRequest, selected_variants: tuple[str, ...]) -> None:
        importer_config = self._build_import_config(request=request, selected_variants=selected_variants)

        if "maxroll" in request.url:
            worker = _Worker(name="maxroll", fn=import_maxroll, config=importer_config)
        elif "d4builds" in request.url:
            worker = _Worker(name="d4builds", fn=import_d4builds, config=importer_config)
        else:
            worker = _Worker(name="mobalytics", fn=import_mobalytics, config=importer_config)

        worker.signals.finished.connect(self._on_worker_finished)
        self._set_generate_button_busy("Generating...")
        THREADPOOL.start(worker)

    def _on_variant_detection_result(self, result: object) -> None:
        request = self._pending_import_request
        self._pending_import_request = None
        if request is None:
            self._reset_generate_button_state()
            return

        variant_options = result if isinstance(result, list) else []
        LOGGER.info(_build_variant_detection_log_message(url=request.url, variant_options=variant_options))

        selected_variants = tuple(variant.id for variant in variant_options if isinstance(variant, ImportVariantOption))
        if len(variant_options) > 1:
            variant_dialog = _VariantSelectionDialog(variant_options, parent=self)
            if not variant_dialog.exec():
                LOGGER.info(PROFILE_IMPORT_CANCELLED_MESSAGE)
                self._reset_generate_button_state()
                return
            selected_variants = variant_dialog.selected_variant_ids()
            if not selected_variants:
                LOGGER.info(PROFILE_IMPORT_CANCELLED_NO_VARIANT_SELECTED_MESSAGE)
                QMessageBox.information(self, "No Variants Selected", "Select at least one variant to import.")
                self._reset_generate_button_state()
                return

        self._start_import_worker(request=request, selected_variants=selected_variants)

    def _on_variant_detection_error(self, error: object) -> None:
        self._pending_import_request = None
        self._reset_generate_button_state()
        LOGGER.error("Failed to load build variants for importer selection: %s", error)
        QMessageBox.critical(self, "Variant Detection Failed", str(error))

    def _set_generate_button_busy(self, text: str) -> None:
        self.generate_button.setEnabled(False)
        self.generate_button.setText(text)

    def _reset_generate_button_state(self) -> None:
        self.generate_button.setEnabled(bool(self.input_box.text().strip()))
        self.generate_button.setText("Generate")

    def _on_worker_finished(self):
        """Handle worker completion."""
        self._reset_generate_button_state()
        self.filename_input_box.clear()

    def closeEvent(self, event):
        """Cleanup when window closes and save geometry."""
        # Save window geometry
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", "true" if self.isMaximized() else "false")

        # Cleanup log handler
        for name in IMPORTER_LOGGER_NAMES:
            logging.getLogger(name).removeHandler(self.log_handler)
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
        try:
            log_entry = self.format(record)
            self.signals.log_message.emit(log_entry)
        except Exception:
            self.handleError(record)

    def _append_log(self, message):
        """Slot that runs in main thread - safe to update GUI."""
        self.text_widget.append(message)
        self.text_widget.ensureCursorVisible()


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
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:
            self.signals.error.emit(exc)
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class _WorkerSignals(QObject):
    error = pyqtSignal(object)
    finished = pyqtSignal()
    result = pyqtSignal(object)
