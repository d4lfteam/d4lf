import copy
import logging
import pathlib

import yaml
from pydantic import ValidationError
from PyQt6.QtCore import QSettings, QSignalBlocker, Qt
from PyQt6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from src.config.loader import IniConfigLoader
from src.config.profile_models import ProfileModel
from src.dataloader import Dataloader
from src.gui.profile_editor.profile_editor import ProfileEditor
from src.item.filter import _UniqueKeyLoader

LOGGER = logging.getLogger(__name__)

PROFILE_TABNAME = "edit profile (beta)"


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("d4lf", "profile_editor")

        self.root = None
        self.current_profile_name = ""
        self.file_path = None
        self.profile_paths = {}
        self.active_profiles = []
        self.inactive_profiles = []
        self.model_editor = None
        self.first_show = True
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(0)

        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)

        tools_groupbox = QGroupBox("Profile")
        tools_groupbox.setStyleSheet("QGroupBox { margin-top: 8px; padding-top: 12px; }")
        tools_groupbox_layout = QVBoxLayout()
        tools_groupbox_layout.setContentsMargins(10, 5, 10, 10)
        button_layout = QHBoxLayout()

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(250)
        self.save_button = QPushButton("Save Profile")
        self.save_button.setFixedWidth(130)
        self.refresh_button = QPushButton("Revert to Saved")
        self.refresh_button.setFixedWidth(130)
        self.profile_combo.currentIndexChanged.connect(self.profile_selection_changed)
        self.save_button.clicked.connect(self.save_yaml)
        self.refresh_button.clicked.connect(self.refresh)

        button_layout.addWidget(self.profile_combo)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        tools_groupbox_layout.addLayout(button_layout)

        instructions_text = QLabel(
            "Select a profile from the dropdown. Click 'Save Profile' to persist your changes. "
            "Click 'Revert to Saved' to discard unsaved edits."
        )
        instructions_text.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        instructions_text.setWordWrap(True)
        tools_groupbox_layout.addWidget(instructions_text)

        tools_groupbox.setLayout(tools_groupbox_layout)
        info_layout.addWidget(tools_groupbox)
        info_layout.addStretch()
        self.main_layout.addLayout(info_layout)

        self.itemTypes = Dataloader().item_types_dict
        self.affixesNames = Dataloader().affix_dict

        self.profile_editor_created = False
        self.editor_container = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_container)
        self.editor_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.editor_container, stretch=1)
        self.setLayout(self.main_layout)
        self.populate_profile_dropdown()

    def has_unsaved_changes(self) -> bool:
        """Return True if the current profile has unsaved changes."""
        if not self.root or not self.original_root:
            return False
        return self.root != self.original_root

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
        if reply == QMessageBox.StandardButton.No:
            self._has_unsaved_changes = False
            return True
        return False

    def confirm_discard_profile_switch(self) -> bool:
        """Prompt user to save changes before switching profiles. Returns True if safe to proceed."""
        reply = QMessageBox.warning(
            self,
            "Unsaved Changes",
            "You have unsaved changes. What would you like to do before switching profiles?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            self.save_yaml()
            return not self.has_unsaved_changes()  # True if save cleared dirty state
        if reply == QMessageBox.StandardButton.Discard:
            self._has_unsaved_changes = False
            return True
        return False  # Cancel

    def create_alert(self, msg: str):
        reply = QMessageBox.warning(self, "Alert", msg, QMessageBox.StandardButton.Ok)
        return reply == QMessageBox.StandardButton.Ok

    def show_tab(self):
        if self.first_show:
            self.first_show = False
            return

    def profile_selection_changed(self, index):
        selected_profile = self.profile_combo.itemData(index, Qt.ItemDataRole.UserRole)
        if selected_profile and selected_profile != self.current_profile_name:
            # Check for unsaved changes before switching
            if self.has_unsaved_changes() and not self.confirm_discard_profile_switch():
                return  # User cancelled
            self.load_selected_profile(selected_profile)

    def load_selected_profile(self, profile_name):
        previous_profile_name = self.current_profile_name
        self.file_path = self.profile_paths[profile_name]
        if self.load_yaml():
            if self.model_editor:
                self.editor_layout.removeWidget(self.model_editor)
                self.model_editor.deleteLater()
            self.model_editor = ProfileEditor(self.root)
            self.editor_layout.addWidget(self.model_editor)
            self.current_profile_name = profile_name
            self.set_current_profile_combo(profile_name)
            LOGGER.info(f"Profile {self.root.name} loaded into profile editor.")
            return

        self.file_path = self.profile_paths.get(previous_profile_name)
        self.set_current_profile_combo(previous_profile_name)

    def add_profile_combo_section(self, label, profiles):
        if not profiles:
            return
        self.profile_combo.addItem(label, None)
        section_index = self.profile_combo.count() - 1
        section_item = self.profile_combo.model().item(section_index)
        section_item.setEnabled(False)
        for profile_name in profiles:
            self.profile_combo.addItem(profile_name, profile_name)

    def set_current_profile_combo(self, profile_name):
        with QSignalBlocker(self.profile_combo):
            index = self.profile_combo.findData(profile_name, Qt.ItemDataRole.UserRole)
            self.profile_combo.setCurrentIndex(index)

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

        with QSignalBlocker(self.profile_combo):
            self.profile_combo.clear()
            self.add_profile_combo_section("--------- Active Profiles ---------", self.active_profiles)
            self.add_profile_combo_section("--------- Inactive Profiles ---------", self.inactive_profiles)

        if not self.active_profiles and not self.inactive_profiles:
            self.current_profile_name = ""
            self.profile_combo.addItem("No profiles found", None)
            no_profiles_item = self.profile_combo.model().item(0)
            no_profiles_item.setEnabled(False)
            self.profile_combo.setEnabled(False)
            self.save_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            return

        self.profile_combo.setEnabled(True)
        self.save_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.select_initial_profile()

    def load(self):
        profile_name = self.current_profile_name
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
            self.editor_layout.addWidget(self.model_editor)
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
            except yaml.YAMLError as e:
                LOGGER.error(f"Error in the YAML file {self.file_path}: {e}")
                return False
            if config is None:
                LOGGER.error(f"Empty YAML file {self.file_path}, please remove it")
                return False
            try:
                self.root = ProfileModel(name=profile_str, **config)
                self.original_root = copy.deepcopy(self.root)
                LOGGER.info(f"File {self.file_path} loaded.")

                # Save last opened profile
                self.settings.setValue("last_opened_profile", filename_without_extension)

            except ValidationError as e:
                error_text = str(e)
                if "GlobalUniques" in error_text and any(
                    field in error_text
                    for field in ("minGreaterAffixCount", "minPercentOfAspect", "minPower", "itemType")
                ):
                    QMessageBox.critical(
                        self,
                        "Profile Validation Failed",
                        (
                            f"PROFILE VALIDATION FAILED: {self.file_path}\n\n"
                            "GlobalUniques no longer supports itemType, minPower, minGreaterAffixCount, "
                            "or minPercentOfAspect.\n\n"
                            "Use regular Affixes rules for item type, power, and item-level greater affix filters. "
                            "Use GlobalUniques affix pools, inherent pools, and unique aspect entries for unique rules."
                        ),
                    )
                elif "minGreaterAffixCount" in error_text:
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

    def save_yaml(self):
        if not self.root or not self.model_editor:
            return
        self.model_editor.save_all()
        self.original_root = copy.deepcopy(self.root)
        # Mark as saved by comparing after save

    def check_close_save(self):
        if self.root and self.original_root != self.root:
            return self.confirm_discard_changes()
        return True

    def refresh(self):
        if not self.load_yaml():
            return
        self.editor_layout.removeWidget(self.model_editor)
        self.model_editor.deleteLater()
        self.model_editor = ProfileEditor(self.root)
        self.editor_layout.addWidget(self.model_editor)
        LOGGER.info(f"Profile {self.root.name} refreshed.")

    def set_unsaved_changes(self, has_changes: bool):
        """Called by ProfileEditor when edits are made."""
        self._has_unsaved_changes = has_changes
