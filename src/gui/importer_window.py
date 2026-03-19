import logging
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QRunnable, QSettings, QSize, Qt, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.gui.importer.d4builds import discover_d4builds_variants, import_d4builds
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import get_maxroll_variant_options, import_maxroll
from src.gui.importer.mobalytics import get_mobalytics_variant_options, import_mobalytics
from src.gui.open_user_config_button import OpenUserConfigButton

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent

ICON_PATH = BASE_DIR / "assets" / "logo.png"

LOGGER = logging.getLogger(__name__)
THREADPOOL = QThreadPool()
IMPORTER_LOGGERS = (
    __name__,
    "src.gui.importer.mobalytics",
    "src.gui.importer.maxroll",
    "src.gui.importer.d4builds",
    "src.gui.importer.common",
)


class ImporterWindow(QMainWindow):
    """Standalone window for Maxroll/D4Builds/Mobalytics importer."""

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

        # Attach directly to each importer logger AND common.py
        for name in IMPORTER_LOGGERS:
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
            "For d4builds you need to specify your browser in the config tab"
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

    def _generate_checkbox(self, name, settings_value, desc, default_value="true") -> QCheckBox:
        def save_setting_change(settings_key):
            self.settings.setValue(settings_key, checkbox.isChecked())

        checkbox = QCheckBox(name)
        checkbox.setChecked(self.settings.value(settings_value, default_value) == "true")
        checkbox.setToolTip(desc)
        checkbox.stateChanged.connect(lambda: save_setting_change(settings_value))
        return checkbox

    def _handle_text_changed(self, text):
        """Enable/disable generate button based on input."""
        self.generate_button.setEnabled(bool(text.strip()))

    def _generate_button_click(self):
        """Handle generate button click."""
        self.log_output.clear()

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
            self.import_gas_checkbox.isChecked(),
            self.require_all_gas_checkbox.isChecked(),
            self.export_paragon_checkbox.isChecked(),
            custom_filename,
        )

        if "maxroll" in url:
            self._discover_variants(
                name="maxroll",
                discover_fn=get_maxroll_variant_options,
                import_fn=import_maxroll,
                import_config=importer_config,
                title="Select Maxroll Variants",
                selection_mode="profile_indices",
                url=url,
            )
            return

        if "d4builds" in url:
            if "var=" in url:
                self._discover_variants(
                    name="d4builds",
                    discover_fn=discover_d4builds_variants,
                    import_fn=import_d4builds,
                    import_config=importer_config,
                    title="Select D4Builds Variants",
                    selection_mode="variant_urls",
                    empty_warning="No D4Builds variants found — importing directly.",
                    config=importer_config,
                )
                return
            self._start_worker(name="d4builds", fn=import_d4builds, config=importer_config)
            return

        if "mobalytics" in url:
            self._discover_variants(
                name="mobalytics",
                discover_fn=get_mobalytics_variant_options,
                import_fn=import_mobalytics,
                import_config=importer_config,
                title="Select Mobalytics Variants",
                selection_mode="variant_urls",
                url=url,
            )
            return

        self._start_worker(name="mobalytics", fn=import_mobalytics, config=importer_config)

    def _start_worker(self, name, fn, **kwargs):
        worker = _Worker(name=name, fn=fn, **kwargs)
        worker.signals.finished.connect(self._on_worker_finished)
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating...")
        THREADPOOL.start(worker)

    def _start_discovery(self, name, fn, on_result, **kwargs):
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Discovering variants...")
        disc = _Worker(name=name, fn=fn, **kwargs)
        disc.signals.result.connect(on_result)
        disc.signals.finished.connect(self._on_discovery_finished)
        THREADPOOL.start(disc)

    def _discover_variants(
        self,
        name: str,
        discover_fn,
        import_fn,
        import_config: ImportConfig,
        title: str,
        selection_mode: str,
        empty_warning: str = "",
        **kwargs,
    ):
        LOGGER.info(f"Discovering {name.title()} variants, please wait...")
        self._start_discovery(
            name=f"{name}_discover",
            fn=discover_fn,
            on_result=lambda variants: self._on_variants_discovered(
                name=name,
                import_fn=import_fn,
                import_config=import_config,
                title=title,
                selection_mode=selection_mode,
                empty_warning=empty_warning,
                variants=variants,
            ),
            **kwargs,
        )

    def _reset_generate_button(self):
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate")

    def _build_selected_config(
        self, config: ImportConfig, variants: list, selected_indices: list[int], selection_mode: str
    ) -> ImportConfig:
        selected_profile_indices = None
        selected_variant_urls = None
        if selection_mode == "profile_indices":
            selected_profile_indices = [getattr(variants[index], "index", index) for index in selected_indices]
        else:
            selected_variant_urls = [
                getattr(variants[index], "url", str(variants[index])) for index in selected_indices
            ]

        return ImportConfig(
            config.url,
            config.import_uniques,
            config.import_aspect_upgrades,
            config.add_to_profiles,
            config.import_greater_affixes,
            config.require_greater_affixes,
            config.export_paragon,
            config.custom_file_name,
            selected_profile_indices,
            selected_variant_urls,
        )

    def _show_variant_selection_dialog(self, title: str, labels: list[str]) -> list[int] | None:
        dialog = _VariantSelectionDialog(title=title, labels=labels, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            LOGGER.info("Import cancelled.")
            self._reset_generate_button()
            return None

        selected_indices = dialog.selected_indices()
        if not selected_indices:
            LOGGER.info("Import cancelled — no variants selected.")
            self._reset_generate_button()
            return None

        return selected_indices

    def _on_worker_finished(self):
        """Handle worker completion."""
        self._reset_generate_button()
        self.filename_input_box.clear()

    def closeEvent(self, event):
        """Cleanup when window closes and save geometry."""
        # Save window geometry
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", "true" if self.isMaximized() else "false")

        # Cleanup log handler
        for name in IMPORTER_LOGGERS:
            logging.getLogger(name).removeHandler(self.log_handler)
        event.accept()

    def _on_variants_discovered(
        self,
        name: str,
        import_fn,
        import_config: ImportConfig,
        title: str,
        selection_mode: str,
        empty_warning: str,
        variants: list,
    ):
        if not variants:
            if empty_warning:
                LOGGER.warning(empty_warning)
            self._start_worker(name=name, fn=import_fn, config=import_config)
            return

        if len(variants) <= 1:
            self._start_worker(name=name, fn=import_fn, config=import_config)
            return

        selected_indices = self._show_variant_selection_dialog(
            title=title, labels=[getattr(variant, "label", str(variant)) for variant in variants]
        )
        if selected_indices is None:
            return

        new_config = self._build_selected_config(
            config=import_config, variants=variants, selected_indices=selected_indices, selection_mode=selection_mode
        )
        self._start_worker(name=name, fn=import_fn, config=new_config)

    def _on_discovery_finished(self):
        """Re-enable button if discovery ended without starting an import."""
        if self.generate_button.text() != "Generating...":
            self._reset_generate_button()


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
        ret = self.fn(*self.args, **self.kwargs)
        self.signals.result.emit(ret)
        self.signals.finished.emit()


class _WorkerSignals(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)


class _VariantSelectionDialog(QDialog):
    """Generic checkbox dialog for selecting importer variants."""

    def __init__(self, title: str, labels: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select which variants to import:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        self._checkboxes: list[QCheckBox] = []
        for label in labels:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            inner_layout.addWidget(checkbox)
            self._checkboxes.append(checkbox)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        sel_all = QPushButton("Select All")
        desel_all = QPushButton("Deselect All")
        sel_all.clicked.connect(self._select_all)
        desel_all.clicked.connect(self._deselect_all)
        btn_row.addWidget(sel_all)
        btn_row.addWidget(desel_all)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_all(self):
        for checkbox in self._checkboxes:
            checkbox.setChecked(True)

    def _deselect_all(self):
        for checkbox in self._checkboxes:
            checkbox.setChecked(False)

    def selected_indices(self) -> list[int]:
        return [index for index, checkbox in enumerate(self._checkboxes) if checkbox.isChecked()]
