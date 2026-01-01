import copy
import logging
import os
import pathlib

import yaml
from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.dataloader import Dataloader
from src.gui.importer.common import ProfileModel
from src.gui.profile_editor.profile_editor import ProfileEditor
from src.item.filter import _UniqueKeyLoader

LOGGER = logging.getLogger(__name__)

PROFILE_TABNAME = "edit profile (beta)"


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()

        self.root = None
        self.file_path = None
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
        self.file_button = QPushButton("Open")
        self.save_button = QPushButton("Save")
        self.refresh_button = QPushButton("Undo Changes")
        self.file_button.clicked.connect(self.load_file)
        self.save_button.clicked.connect(self.save_yaml)
        self.refresh_button.clicked.connect(self.refresh)
        tools_groupbox_layout.addWidget(self.file_button)
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
            "You load a profile by clicking the 'Open' button. Click 'Save' to save your changes. Click 'Undo Changes' to revert your changes."
        )

        instructions_text.setFixedHeight(50)
        self.main_layout.addWidget(instructions_text)
        self.setLayout(self.main_layout)

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
            if self.load():
                self.create_profile_editor()

    def load_file(self):
        if self.open_file():
            if self.model_editor:
                self.scrollable_layout.removeWidget(self.model_editor)
            self.model_editor = ProfileEditor(self.root)
            self.scrollable_layout.addWidget(self.model_editor)
            LOGGER.info(f"Profile {self.root.name} loaded into profile editor.")

    def open_file(self):
        custom_profile_path = IniConfigLoader().user_dir / "profiles"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open YAML File", str(custom_profile_path), "YAML Files (*.yaml *.yml)"
        )
        if file_path:
            self.file_path = file_path
            return self.load_yaml()
        return False

    def load(self):
        # Force reload config to get latest last_opened_profile
        IniConfigLoader().load()

        profiles: list[str] = IniConfigLoader().general.profiles
        custom_profile_path = IniConfigLoader().user_dir / "profiles"

        # Try to load last opened profile first
        last_opened = getattr(IniConfigLoader().general, "last_opened_profile", None)
        if last_opened and not self.file_path:
            custom_file_path = custom_profile_path / f"{last_opened}.yaml"
            if custom_file_path.is_file():
                self.file_path = custom_file_path
                return self.load_yaml()

        if not self.file_path and profiles:  # at start, set default file to build in params.ini
            custom_file_path = custom_profile_path / f"{profiles[0]}.yaml"
            if not custom_file_path.is_file():
                LOGGER.error(f"Could not load profile {profiles[0]}. Checked: {custom_file_path}")
                return False
            self.file_path = custom_file_path
            return self.load_yaml()
        if not self.file_path and not profiles:
            return self.open_file()
        return False

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
        filename = os.path.basename(self.file_path)
        filename_without_extension = filename.rsplit(".", 1)[0]
        profile_str = filename_without_extension.replace("_", " ")
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
                IniConfigLoader().save_value("general", "last_opened_profile", filename_without_extension)  # ← ADD THIS

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
            filename = os.path.basename(self.file_path)  # Get the filename from the full path
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
