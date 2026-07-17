import logging

from PyQt6.QtCore import QSettings, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import (
    QComboBox,
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

from src.dataloader import Dataloader
from src.profiles import (
    EmptyError,
    Failed,
    Loaded,
    LoadedProfile,
    ProfileSession,
    Saved,
    ValidationDiffers,
    ValidationError,
    YamlError,
)
from src.profiles.editor import ProfileEditor
from src.profiles.editor.session_store import QSettingsLastOpenedStore

LOGGER = logging.getLogger(__name__)

PROFILE_TABNAME = "edit profile (beta)"


class ProfileTab(QWidget):
    profile_saved = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("d4lf", "profile_editor")
        self.session = ProfileSession(last_opened_store=QSettingsLastOpenedStore(self.settings))
        self.root = None
        self.current_profile_name = ""
        self.file_path = None
        self.loaded_profile: LoadedProfile | None = None
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

        tools_groupbox = QGroupBox("Profile")
        tools_groupbox_layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.save_button = QPushButton("Save")
        self.refresh_button = QPushButton("Undo Changes")
        self.profile_combo.currentIndexChanged.connect(self.profile_selection_changed)
        self.save_button.clicked.connect(self.save_yaml)
        self.refresh_button.clicked.connect(self.refresh)
        tools_groupbox_layout.addWidget(self.profile_combo)
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
            "Select a profile from the dropdown. Click 'Save' to save your changes. Click 'Undo Changes' to revert your changes."
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

    def profile_selection_changed(self, index):
        selected_profile = self.profile_combo.itemData(index, Qt.ItemDataRole.UserRole)
        if selected_profile and selected_profile != self.current_profile_name:
            self.load_selected_profile(selected_profile)

    def load_selected_profile(self, profile_name):
        previous_profile_name = self.current_profile_name
        self.file_path = self.profile_paths[profile_name]
        if self.load_yaml():
            loaded_profile = self.loaded_profile
            root = self.root
            if loaded_profile is None or root is None:
                self.file_path = self.profile_paths.get(previous_profile_name)
                self.set_current_profile_combo(previous_profile_name)
                return
            self._set_model_editor(loaded_profile)
            self.current_profile_name = profile_name
            self.set_current_profile_combo(profile_name)
            LOGGER.info(f"Profile {root.name} loaded into profile editor.")
            return

        self.file_path = self.profile_paths.get(previous_profile_name)
        self.set_current_profile_combo(previous_profile_name)

    def add_profile_combo_section(self, label, profiles):
        if not profiles:
            return
        self.profile_combo.addItem(label, None)
        section_index = self.profile_combo.count() - 1
        model = self.profile_combo.model()
        if not isinstance(model, QStandardItemModel):
            return
        section_item = model.item(section_index)
        if section_item is None:
            return
        section_item.setEnabled(False)
        for profile_name in profiles:
            self.profile_combo.addItem(profile_name, profile_name)

    def set_current_profile_combo(self, profile_name):
        with QSignalBlocker(self.profile_combo):
            index = self.profile_combo.findData(profile_name, Qt.ItemDataRole.UserRole)
            self.profile_combo.setCurrentIndex(index)

    def populate_profile_dropdown(self):
        catalog = self.session.discover()
        self.profile_paths = catalog.paths
        self.active_profiles = catalog.active
        self.inactive_profiles = catalog.inactive

        with QSignalBlocker(self.profile_combo):
            self.profile_combo.clear()
            self.add_profile_combo_section("--------- Active Profiles ---------", self.active_profiles)
            self.add_profile_combo_section("--------- Inactive Profiles ---------", self.inactive_profiles)

        if not self.active_profiles and not self.inactive_profiles:
            self.current_profile_name = ""
            self.profile_combo.addItem("No profiles found", None)
            model = self.profile_combo.model()
            if isinstance(model, QStandardItemModel):
                no_profiles_item = model.item(0)
                if no_profiles_item is not None:
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
        last_opened = self.session.last_opened_profile()
        if last_opened in self.profile_paths:
            self.load_selected_profile(last_opened)
            return

        if self.active_profiles:
            self.load_selected_profile(self.active_profiles[0])
            return

        self.load_selected_profile(self.inactive_profiles[0])

    def create_profile_editor(self):
        loaded_profile = self.loaded_profile
        root = self.root
        if not self.profile_editor_created and loaded_profile is not None and root is not None:
            self._set_model_editor(loaded_profile)
            self.profile_editor_created = True
            LOGGER.info(f"Profile {root.name} loaded into profile editor.")

    def load_yaml(self):
        if not self.file_path:
            LOGGER.debug("No profile loaded, cannot refresh.")
            return False
        self.root = None
        load_result = self.session.load(self.file_path.stem)
        if isinstance(load_result, YamlError):
            LOGGER.error(load_result.message)
            return False
        if isinstance(load_result, EmptyError):
            LOGGER.error(load_result.message)
            return False
        if isinstance(load_result, ValidationError):
            if load_result.guidance:
                QMessageBox.critical(self, "Profile Validation Failed", load_result.guidance)
            else:
                QMessageBox.critical(self, "Validation Error", load_result.message)
            return False
        if not isinstance(load_result, Loaded):
            return False

        self.loaded_profile = load_result.loaded_profile
        self.root = self.loaded_profile.profile
        return True

    def save_yaml(self):
        if self.model_editor is None:
            return
        save_result = self.session.save(self.model_editor.get_current_model())
        if isinstance(save_result, Saved):
            QMessageBox.information(self, "Info", f"Profile saved successfully to {save_result.saved.path.name}")
            self.profile_saved.emit(self.model_editor.get_current_model().name)
            self.root = self.model_editor.get_current_model()
            return
        if isinstance(save_result, ValidationDiffers):
            save_coerced = QMessageBox.warning(
                self,
                "Warning",
                "The profile model might not be valid. Do you still want to save your changes ?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard,
            )
            if save_coerced == QMessageBox.StandardButton.Save:
                loaded_profile = self.loaded_profile
                if loaded_profile is None:
                    return
                force_result = self.session.save(save_result.coerced_model, force=True)
                if isinstance(force_result, Saved):
                    QMessageBox.information(
                        self, "Info", f"Profile saved successfully to {force_result.saved.path.name}"
                    )
                    self.loaded_profile = LoadedProfile(
                        path=loaded_profile.path, name=loaded_profile.name, profile=save_result.coerced_model
                    )
                    self._set_model_editor(self.loaded_profile)
                    self.root = save_result.coerced_model
                    self.profile_saved.emit(save_result.coerced_model.name)
                    return
                if isinstance(force_result, Failed):
                    QMessageBox.critical(self, "Error", f"Failed to save profile: {force_result.error}")
                    return
            else:
                QMessageBox.information(self, "Info", "Profile not saved.")
            return
        if isinstance(save_result, Failed):
            QMessageBox.critical(self, "Error", f"Failed to save profile: {save_result.error}")

    def check_close_save(self):
        if self.root and self.model_editor and self.session.is_dirty(self.model_editor.get_current_model()):
            return self.confirm_discard_changes()
        return True

    def refresh(self):
        if not self.load_yaml():
            return
        loaded_profile = self.loaded_profile
        root = self.root
        if loaded_profile is None or root is None:
            return
        self._set_model_editor(loaded_profile)
        LOGGER.info(f"Profile {root.name} refreshed.")

    def _set_model_editor(self, loaded_profile: LoadedProfile) -> None:
        if self.model_editor:
            self.scrollable_layout.removeWidget(self.model_editor)
            self.model_editor.deleteLater()
        self.model_editor = ProfileEditor(loaded_profile)
        self.scrollable_layout.addWidget(self.model_editor)
