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
from src.importing.gui.support import ImportWorker
from src.settings import get_settings

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]
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
IMPORTER_WINDOW_LOGGERS = (
    "src.importing.mobalytics",
    "src.importing.maxroll",
    "src.importing.d4builds",
    "src.importing.infinitybuilds",
    "src.importing.gui.support",
    "src.importing.pipeline",
    "src.profiles",
)


class ImporterWindow(QMainWindow):
    """Standalone window for importing profiles from supported build guides."""

    import_completed = pyqtSignal()

    def __init__(self, parent=None, accent_color: str | None = None):
        super().__init__(parent)
        if accent_color is not None:
            set_accent_color(accent_color)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Settings for persistent window geometry and importer options.
        self.settings = QSettings("d4lf", "ImporterWindow")
        self.is_generating = False
        self.setWindowTitle("Profile Importer - Maxroll / D4Builds / Mobalytics / InfinityBuilds")
        self.setMinimumSize(700, 600)
        # Restore window geometry.
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
        instructions.setText(
            "You can link either the build guide or a direct link to the specific planner.\n\n"
            "https://maxroll.gg/d4/build-guides/tornado-druid-guide\n"
            "or\nhttps://maxroll.gg/d4/planner/cm6pf0xa#5\n"
            "or\nhttps://d4builds.gg/builds/ef414fbd-81cd-49d1-9c8d-4938b278e2ee\n"
            "or\nhttps://mobalytics.gg/diablo-4/builds/barbarian/bash\n"
            "or\nhttps://infinitybuilds.gg/en/builds/barbarian-fL8P6vVSqI\n\n"
            f"It will create a file based on the label of the build in the planner in: "
            f"{get_settings().user_dir / 'profiles'}\n\n"
            "For d4builds you need to specify your browser in the Settings window"
        )
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
        self.import_aspect_upgrades_checkbox = self._generate_checkbox(
            "Import Aspect Upgrades",
            "import_aspect_upgrades",
            "If legendary aspects are in the build, do you want an aspect upgrades section generated for them?",
        )
        self.import_charms_checkbox = self._generate_checkbox(
            "Import Charms", "import_charms", "If a build has charms, should they be included in the imported profile?"
        )
        self.import_seals_checkbox = self._generate_checkbox(
            "Import Seals", "import_seals", "If a build has seals, should they be included in the imported profile?"
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
                custom_file_name=custom_filename,
                filename_parts=self._selected_filename_parts(),
            ),
        )
        worker = ImportWorker(request=request, finished=self._on_worker_finished)
        self.is_generating = True
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating...")
        THREADPOOL.start(worker)

    def _on_worker_finished(self):
        self.is_generating = False
        self.generate_button.setText("Generate")
        self.filename_input_box.clear()
        self._update_generate_button_state()
        self.import_completed.emit()

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
