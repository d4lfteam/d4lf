import copy
import logging
import pathlib

import yaml
from pydantic import ValidationError
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.dataloader import Dataloader
from src.gui.importer.gui_common import ProfileModel
from src.gui.profile_editor.profile_editor import ProfileEditor
from src.item.filter import _UniqueKeyLoader

LOGGER = logging.getLogger(__name__)

PROFILE_TABNAME = "edit profile (beta)"


class ProfilePickerDialog(QDialog):
    def __init__(self, parent, active_profiles, inactive_profiles, current_profile):
        super().__init__(parent)
        self.setWindowTitle("Select profile")
        self.setGeometry(0, 0, 700, 500)

        overall_layout = QVBoxLayout()
        list_widget_layout = QGridLayout()

        self.disabled_profiles_list_widget = QListWidget()
        self.disabled_profiles_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.disabled_profiles_list_widget.itemDoubleClicked.connect(self.accept)
        self.disabled_profiles_list_widget.itemSelectionChanged.connect(self.clear_enabled_selection)

        self.enabled_profiles_list_widget = QListWidget()
        self.enabled_profiles_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.enabled_profiles_list_widget.itemDoubleClicked.connect(self.accept)
        self.enabled_profiles_list_widget.itemSelectionChanged.connect(self.clear_disabled_selection)

        for profile_name in inactive_profiles:
            item = QListWidgetItem(profile_name, self.disabled_profiles_list_widget)
            if profile_name == current_profile:
                self.disabled_profiles_list_widget.setCurrentItem(item)

        for profile_name in active_profiles:
            item = QListWidgetItem(profile_name, self.enabled_profiles_list_widget)
            if profile_name == current_profile:
                self.enabled_profiles_list_widget.setCurrentItem(item)

        list_widget_layout.addWidget(QLabel("Disabled Profiles"), 0, 0)
        list_widget_layout.addWidget(self.disabled_profiles_list_widget, 1, 0)
        list_widget_layout.addWidget(QLabel("Enabled Profiles"), 0, 1)
        list_widget_layout.addWidget(self.enabled_profiles_list_widget, 1, 1)
        overall_layout.addLayout(list_widget_layout)

        ok_cancel_buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(ok_cancel_buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        overall_layout.addWidget(self.buttonBox)
        self.setLayout(overall_layout)

    def clear_disabled_selection(self):
        if self.enabled_profiles_list_widget.selectedItems():
            self.disabled_profiles_list_widget.clearSelection()

    def clear_enabled_selection(self):
        if self.disabled_profiles_list_widget.selectedItems():
            self.enabled_profiles_list_widget.clearSelection()

    def get_selected_profile(self):
        selected_enabled_profiles = self.enabled_profiles_list_widget.selectedItems()
        if selected_enabled_profiles:
            return selected_enabled_profiles[0].text()

        selected_disabled_profiles = self.disabled_profiles_list_widget.selectedItems()
        if selected_disabled_profiles:
            return selected_disabled_profiles[0].text()
        return ""


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("d4lf", "profile_editor")

        self.root = None
        self.file_path = None
        self.profile_paths = {}
        self.active_profiles = []
        self.inactive_profiles = []
        self.model_editor = None
        self.first_show = True
        self.main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        self.scrollable_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidgetResizable(True)

        info_layout = QHBoxLayout()
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        profile_groupbox = QGroupBox("Profile Loaded")
        profile_groupbox_layout = QVBoxLayout()
        self.filenameLabel = QLabel("")
        self.filenameLabel.setStyleSheet("font-size: 12pt;")
        profile_groupbox_layout.addWidget(self.filenameLabel)
        profile_groupbox.setLayout(profile_groupbox_layout)
        info_layout.addWidget(profile_groupbox)

        tools_groupbox = QGroupBox("Tools")
        tools_groupbox_layout = QHBoxLayout()
        self.current_profile_line_edit = QLineEdit()
        self.current_profile_line_edit.setReadOnly(True)
        self.profile_picker_button = QPushButton("...")
        self.profile_picker_button.setMinimumWidth(20)
        self.save_button = QPushButton("Save")
        self.refresh_button = QPushButton("Undo Changes")
        self.profile_picker_button.clicked.connect(self.launch_profile_picker)
        self.save_button.clicked.connect(self.save_yaml)
        self.refresh_button.clicked.connect(self.refresh)
        tools_groupbox_layout.addWidget(self.current_profile_line_edit)
        tools_groupbox_layout.addWidget(self.profile_picker_button)
        tools_groupbox_layout.addWidget(self.save_button)
        tools_groupbox_layout.addWidget(self.refresh_button)
        tools_groupbox.setLayout(tools_groupbox_layout)
        info_layout.addWidget(tools_groupbox)
        self.main_layout.addLayout(info_layout)

        self.itemTypes = Dataloader().item_types_dict
        self.affixesNames = Dataloader().affix_dict

        self.profile_editor_created = False
        scroll_widget.setLayout(self.scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(scroll_area)
        instructions_label = QLabel("Instructions")
        self.main_layout.addWidget(instructions_label)

        instructions_text = QTextBrowser()
        instructions_text.append(
            "Select a profile with the '...' button. Click 'Save' to save your changes. Click 'Undo Changes' to revert your changes."
        )

        instructions_text.setFixedHeight(50)
        self.main_layout.addWidget(instructions_text)
        self.setLayout(self.main_layout)
        self.populate_profile_dropdown()

    def confirm_discard_changes(self):
        reply = QMessageBox.warning(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save them before closing?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.save_yaml()
            return True
        return reply == QMessageBox.StandardButton.No

    def create_alert(self, msg: str):
        reply = QMessageBox.warning(self, "Alert", msg, QMessageBox.StandardButton.Ok)
        return reply == QMessageBox.StandardButton.Ok

    def show_tab(self):
        if self.first_show:
            self.first_show = False
            return

    def launch_profile_picker(self):
        profile_picker = ProfilePickerDialog(
            self, self.active_profiles, self.inactive_profiles, self.current_profile_line_edit.text()
        )
        if profile_picker.exec():
            selected_profile = profile_picker.get_selected_profile()
            if selected_profile:
                self.load_selected_profile(selected_profile)

    def load_selected_profile(self, profile_name):
        self.file_path = self.profile_paths[profile_name]
        if self.load_yaml():
            if self.model_editor:
                self.scrollable_layout.removeWidget(self.model_editor)
            self.model_editor = ProfileEditor(self.root)
            self.scrollable_layout.addWidget(self.model_editor)
            self.current_profile_line_edit.setText(profile_name)
            LOGGER.info(f"Profile {self.root.name} loaded into profile editor.")

    def populate_profile_dropdown(self):
        custom_profile_path = IniConfigLoader().user_dir / "profiles"
        custom_profile_path.mkdir(parents=True, exist_ok=True)
        self.profile_paths = {
            profile_file.stem: profile_file
            for profile_file in custom_profile_path.iterdir()
            if profile_file.is_file() and profile_file.suffix.lower() in {".yaml", ".yml"}
        }

        self.active_profiles = []
        for profile_name in IniConfigLoader().general.profiles:
            if profile_name in self.profile_paths and profile_name not in self.active_profiles:
                self.active_profiles.append(profile_name)
        self.inactive_profiles = sorted(
            (profile_name for profile_name in self.profile_paths if profile_name not in self.active_profiles),
            key=str.lower,
        )

        if not self.active_profiles and not self.inactive_profiles:
            self.current_profile_line_edit.setText("No profiles found")
            self.profile_picker_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            return

        self.profile_picker_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.select_initial_profile()

    def load(self):
        profile_name = self.current_profile_line_edit.text()
        if not self.file_path and profile_name in self.profile_paths:
            self.file_path = self.profile_paths[profile_name]
            return self.load_yaml()
        return False

    def select_initial_profile(self):
        last_opened = self.settings.value("last_opened_profile", None, type=str)
        if last_opened in self.profile_paths:
            self.load_selected_profile(last_opened)
            return

        if self.active_profiles:
            self.load_selected_profile(self.active_profiles[0])
            return

        self.load_selected_profile(self.inactive_profiles[0])

    def create_profile_editor(self):
        if not self.profile_editor_created and self.root:
            self.model_editor = ProfileEditor(self.root)
            self.scrollable_layout.addWidget(self.model_editor)
            self.profile_editor_created = True
            LOGGER.info(f"Profile {self.root.name} loaded into profile editor.")

    def load_yaml(self):
        if not self.file_path:
            LOGGER.debug("No profile loaded, cannot refresh.")
            return False
        filename = pathlib.Path(self.file_path).name  # Get the filename from the full path
        filename_without_extension = filename.rsplit(".", 1)[0]  # Remove the extension
        profile_str = filename_without_extension.replace("_", " ")  # Replace underscores with spaces
        self.root = None
        with pathlib.Path(self.file_path).open(encoding="utf-8") as f:
            try:
                config = yaml.load(stream=f, Loader=_UniqueKeyLoader)
            except Exception as e:
                LOGGER.error(f"Error in the YAML file {self.file_path}: {e}")
                return False
            if config is None:
                LOGGER.error(f"Empty YAML file {self.file_path}, please remove it")
                return False
            try:
                self.root = ProfileModel(name=profile_str, **config)
                self.original_root = copy.deepcopy(self.root)
                LOGGER.info(f"File {self.file_path} loaded.")
                self.update_filename_label()

                # Save last opened profile
                self.settings.setValue("last_opened_profile", filename_without_extension)

            except ValidationError as e:
                if "minGreaterAffixCount" in str(e):
                    error_text = (
                        f"PROFILE VALIDATION FAILED: {self.file_path}\n\n"
                        "You are using an old, outdated field that must be removed from your profile.\n\n"
                        "WRONG (old way - pool level):\n"
                        "- Ring:\n"
                        "    itemType: [ring]\n"
                        "    minPower: 100\n"
                        "    affixPool:\n"
                        "    - count:\n"
                        "      - {name: strength}\n"
                        "      minCount: 2\n"
                        "      minGreaterAffixCount: 1  ← DELETE THIS LINE\n\n"
                        "CORRECT (new way - item level):\n"
                        "- Ring:\n"
                        "    itemType: [ring]\n"
                        "    minPower: 100\n"
                        "    minGreaterAffixCount: 1  ← PUT IT HERE INSTEAD\n"
                        "    affixPool:\n"
                        "    - count:\n"
                        "      - {name: strength}\n"
                        "      minCount: 2\n"
                        "      # NO minGreaterAffixCount here anymore!\n\n"
                        f"ACTION REQUIRED: Please make the above adjustments in:\n{self.file_path}"
                    )
                    QMessageBox.critical(self, "Profile Validation Failed", error_text)
                else:
                    QMessageBox.critical(self, "Validation Error", f"Validation error in {self.file_path}:\n\n{e}")
                return False
        return True

    def update_filename_label(self):
        if self.file_path:
            filename = pathlib.Path(self.file_path).name  # Get the filename from the full path
            filename_without_extension = filename.rsplit(".", 1)[0]  # Remove the extension
            display_name = filename_without_extension.replace("_", " ")  # Replace underscores with spaces
            self.filenameLabel.setText(display_name)

    def save_yaml(self):
        self.original_root = copy.deepcopy(self.root)
        self.model_editor.save_all()

    def check_close_save(self):
        if self.root and self.original_root != self.root:
            return self.confirm_discard_changes()
        return True

    def refresh(self):
        if not self.load_yaml():
            return
        self.scrollable_layout.removeWidget(self.model_editor)
        self.model_editor = ProfileEditor(self.root)
        self.scrollable_layout.addWidget(self.model_editor)
        LOGGER.info(f"Profile {self.root.name} refreshed.")
