import logging
import sys
from pathlib import Path
from typing import override

from PyQt6.QtCore import QPoint, QSettings, QSize, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QIcon
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

from src.desktop.activity import QtLogHandler
from src.desktop.widgets import CheckmarkCheckBox, set_accent_color
from src.importing import DEFAULT_FILENAME_PARTS, FilenamePart, ImportOptions, ImportRequest
from src.importing.gui.constants import (
    FILENAME_PART_LABELS,
    GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP,
    IMPORTER_WINDOW_LOGGERS,
    INSTRUCTIONS_TEXT,
)
from src.importing.gui.dialogs import select_variants_dialog
from src.importing.gui.support import FetchVariantsWorker, ImportWorker
from src.settings import get_settings

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
ICON_PATH = BASE_DIR / "assets" / "logo.png"
LOGGER = logging.getLogger(__name__)
THREADPOOL = QThreadPool()


class ImporterWindow(QMainWindow):
    """Standalone window for importing profiles from supported build guides."""

    import_completed = pyqtSignal()

    import_aspect_upgrades_checkbox: CheckmarkCheckBox
    import_charms_checkbox: CheckmarkCheckBox
    import_seals_checkbox: CheckmarkCheckBox
    add_to_profiles_checkbox: CheckmarkCheckBox
    import_gas_checkbox: CheckmarkCheckBox
    require_all_gas_checkbox: CheckmarkCheckBox
    export_paragon_checkbox: CheckmarkCheckBox
    multi_build_checkbox: CheckmarkCheckBox
    input_box: QLineEdit
    filename_input_box: QLineEdit
    filename_parts_summary_label: QLabel
    generate_button: QPushButton
    log_output: QTextEdit

    def __init__(self, parent=None, accent_color: str | None = None):
        super().__init__(parent)
        if accent_color is not None:
            set_accent_color(accent_color)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.settings = QSettings("d4lf", "ImporterWindow")
        self.is_generating = False
        self.setWindowTitle("Profile Importer - Maxroll / D4Builds / Mobalytics / InfinityBuilds")
        self.setMinimumSize(700, 600)
        self.resize(self.settings.value("size", QSize(700, 600)))
        self.move(self.settings.value("pos", QPoint(100, 100)))
        if self.settings.value("maximized", "false") == "true":
            self.showMaximized()
        self._build_ui()
        # Setup logging.
        self.log_handler = QtLogHandler(self.log_output)
        for name in IMPORTER_WINDOW_LOGGERS:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(self.log_handler)

    def _build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        self._build_url_row(layout)
        self._build_filename_row(layout)
        self._build_options(layout)
        layout.addWidget(QLabel("Log:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        layout.addWidget(QLabel("Instructions:"))
        instructions = QTextEdit()
        instructions.setText(INSTRUCTIONS_TEXT.format(user_dir=get_settings().user_dir))
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(200)
        instructions.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(instructions)

    def _build_url_row(self, layout: QVBoxLayout):
        # URL input.
        row = QHBoxLayout()
        row.addWidget(QLabel("URL:"))
        self.input_box = QLineEdit()
        self.input_box.textChanged.connect(self._update_generate_button_state)
        row.addWidget(self.input_box)
        self.generate_button = QPushButton("Generate")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate_button_click)
        row.addWidget(self.generate_button)
        layout.addLayout(row)

    def _build_filename_row(self, layout: QVBoxLayout):
        # Filename input.
        row = QHBoxLayout()
        row.addWidget(QLabel("Custom file name:"))
        self.filename_input_box = QLineEdit()
        self.filename_input_box.setPlaceholderText("Leave blank for default filename")
        self.filename_input_box.textChanged.connect(self._update_generate_button_state)
        row.addWidget(self.filename_input_box)
        self.filename_parts_button = QPushButton("Default filename includes...")
        self.filename_parts_menu = QMenu(self.filename_parts_button)
        self.filename_part_actions: dict[FilenamePart, QAction] = {}
        for part in DEFAULT_FILENAME_PARTS:
            action = QAction(FILENAME_PART_LABELS[part], self.filename_parts_menu)
            action.setCheckable(True)
            action.setChecked(self._filename_part_setting(part))
            action.toggled.connect(lambda checked, part=part: self._handle_filename_part_toggled(part, checked))
            self.filename_parts_menu.addAction(action)
            self.filename_part_actions[part] = action
        self.filename_parts_button.setMenu(self.filename_parts_menu)
        row.addWidget(self.filename_parts_button)
        layout.addLayout(row)
        self.filename_parts_summary_label = QLabel()
        layout.addWidget(self.filename_parts_summary_label)
        self._update_filename_parts_summary()
        self._update_generate_button_state()

    def _build_options(self, layout: QVBoxLayout):
        # fmt: off
        checkboxes = [
            ("import_aspect_upgrades_checkbox", "Import Aspect Upgrades", "import_aspect_upgrades", "If legendary aspects are in the build, do you want an aspect upgrades section generated for them?", "true"),
            ("import_charms_checkbox", "Import Charms", "import_charms", "If a build has charms, should they be included in the imported profile?", "true"),
            ("import_seals_checkbox", "Import Seals", "import_seals", "If a build has seals, should they be included in the imported profile?", "true"),
            ("add_to_profiles_checkbox", "Add to profiles", "add_to_profiles", "Do you want to add this build to your active profiles upon generating?", "false"),
            ("import_gas_checkbox", "Include GAs", "import_greater_affixes", "Include the greater affix tags from the build, making it look for GAs?", "false"),
            ("require_all_gas_checkbox", "Require all GAs", "require_all_greater_affixes", "Are the GAs required to match the item?", "false"),
            ("export_paragon_checkbox", "Export Paragon", "export_paragon", "Export paragon boards for the paragon overlay?", "false"),
            ("multi_build_checkbox", "Multi Build Import", "multi_build_import", "Import multiple builds from the link?", "false"),
        ]
        # fmt: on
        for name, label, setting, tooltip, default in checkboxes:
            setattr(self, name, self._generate_checkbox(label, setting, tooltip, default))

        self.require_all_gas_checkbox.setEnabled(self.import_gas_checkbox.isChecked())
        if not self.import_gas_checkbox.isChecked():
            self.require_all_gas_checkbox.setChecked(False)
        self.import_gas_checkbox.stateChanged.connect(self._update_greater_affix_dependency)
        grid = QGridLayout()
        grid.setContentsMargins(0, 10, 0, 10)
        grid.setSpacing(10)
        grid.addWidget(self.import_aspect_upgrades_checkbox, 0, 0)
        grid.addWidget(self.import_charms_checkbox, 0, 1)
        grid.addWidget(self.import_seals_checkbox, 0, 2)
        grid.addWidget(self.import_gas_checkbox, 1, 0)
        grid.addWidget(self.require_all_gas_checkbox, 1, 1)
        grid.addWidget(self.export_paragon_checkbox, 1, 2)
        grid.addWidget(self.add_to_profiles_checkbox, 2, 0)
        grid.addWidget(self.multi_build_checkbox, 2, 1)
        layout.addLayout(grid)

    def _generate_checkbox(self, name: str, setting: str, description: str, default: str = "true"):
        checkbox = CheckmarkCheckBox(name)
        value = self.settings.value(setting, default)
        checkbox.setChecked(value is True or str(value).casefold() == "true")
        checkbox.setToolTip(description)
        checkbox.stateChanged.connect(lambda: self.settings.setValue(setting, checkbox.isChecked()))
        return checkbox

    def _update_greater_affix_dependency(self):
        enabled = self.import_gas_checkbox.isChecked()
        self.require_all_gas_checkbox.setEnabled(enabled)
        if not enabled:
            self.require_all_gas_checkbox.setChecked(False)

    def _filename_part_setting(self, part: FilenamePart) -> bool:
        value = self.settings.value(self._filename_part_setting_key(part), "true")
        return value is True or str(value).casefold() == "true"

    def _handle_filename_part_toggled(self, part: FilenamePart, checked: bool):
        self.settings.setValue(self._filename_part_setting_key(part), checked)
        self._update_filename_parts_summary()
        self._update_generate_button_state()

    def _selected_filename_parts(self) -> tuple[FilenamePart, ...]:
        return tuple(part for part in DEFAULT_FILENAME_PARTS if self.filename_part_actions[part].isChecked())

    def _update_filename_parts_summary(self):
        labels = [FILENAME_PART_LABELS[part] for part in self._selected_filename_parts()]
        self.filename_parts_summary_label.setText(
            f"Default file name: {'_'.join(labels) + '.yaml' if labels else 'none'}"
        )

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
        if not self.generate_button.isEnabled():
            return
        self.log_output.clear()
        custom_filename = self.filename_input_box.text().split(".", 1)[0].strip() or None
        request = ImportRequest(
            url=self.input_box.text().strip(),
            options=ImportOptions(
                import_aspect_upgrades=self.import_aspect_upgrades_checkbox.isChecked(),
                import_charms=self.import_charms_checkbox.isChecked(),
                import_seals=self.import_seals_checkbox.isChecked(),
                add_to_profiles=self.add_to_profiles_checkbox.isChecked(),
                import_greater_affixes=self.import_gas_checkbox.isChecked(),
                require_greater_affixes=self.require_all_gas_checkbox.isChecked(),
                export_paragon=self.export_paragon_checkbox.isChecked(),
                multi_build=self.multi_build_checkbox.isChecked(),
                custom_file_name=custom_filename,
                filename_parts=self._selected_filename_parts(),
            ),
        )
        # Store the current request so we can re-use it for persistence if multi_build is used
        self._current_request = request
        if request.options.multi_build:
            worker = FetchVariantsWorker(request=request, finished=self._on_worker_finished)
            worker.signals.variants_extracted.connect(self._on_variants_extracted)
        else:
            worker = ImportWorker(request=request, finished=self._on_worker_finished)

        self.is_generating = True
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating...")
        THREADPOOL.start(worker)

    def _on_worker_finished(self):
        if hasattr(self, "_waiting_for_user_selection") and self._waiting_for_user_selection:
            return
        self.is_generating = False
        self.generate_button.setText("Generate")
        self.filename_input_box.clear()
        self._update_generate_button_state()
        self.import_completed.emit()

    def _on_variants_extracted(self, variants):
        self._waiting_for_user_selection = True
        # variants is a list of VariantMetadata
        # We need the source_name, but we don't have it explicitly. Let's just pass "the build guide"
        source_name = "the build guide"
        selected_ids = select_variants_dialog(self, variants, source_name)
        if selected_ids is None or not selected_ids:
            LOGGER.info("No variants selected or dialog cancelled, aborting import.")
            self._waiting_for_user_selection = False
            self._on_worker_finished()
            return

        LOGGER.info(f"User selected {len(selected_ids)} variant(s). Generating...")
        self.generate_button.setText("Saving...")
        worker = ImportWorker(
            request=self._current_request, finished=self._on_persist_finished, selected_variant_ids=selected_ids
        )
        THREADPOOL.start(worker)

    def _on_persist_finished(self):
        self._waiting_for_user_selection = False
        self._on_worker_finished()

    @staticmethod
    def _filename_part_setting_key(part: FilenamePart) -> str:
        return f"filename_part_{part.value}"

    @override
    def closeEvent(self, a0: QCloseEvent | None):
        # PyQt exposes `a0` as a keyword, so the override must retain that public name.
        if not self.isMaximized():
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", "true" if self.isMaximized() else "false")
        # Cleanup log handler.
        for name in IMPORTER_WINDOW_LOGGERS:
            logging.getLogger(name).removeHandler(self.log_handler)
        if a0 is not None:
            a0.accept()
