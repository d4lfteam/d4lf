import json
import logging
import os

import yaml
from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
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

from gui.d4lfitem import D4LFItem
from gui.dialog import CreateItem, DeleteItem, MinCountDialog, MinGreaterDialog, MinPowerDialog
from src.config import BASE_DIR
from src.config.loader import IniConfigLoader
from src.gui.importer.common import ProfileModel, save_as_profile
from src.item.filter import _UniqueKeyLoader

LOGGER = logging.getLogger(__name__)

PROFILE_TABNAME = "edit profile (beta)"


class ProfileTab(QWidget):
    def __init__(self):
        super().__init__()

        self.root = None
        self.file_path = None
        self.main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
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
        self.file_button = QPushButton("File")
        self.save_button = QPushButton("Save")
        self.refresh_button = QPushButton("Refresh")
        self.file_button.clicked.connect(self.load)
        self.save_button.clicked.connect(self.save_yaml)
        self.refresh_button.clicked.connect(self.refresh)
        tools_groupbox_layout.addWidget(self.file_button)
        tools_groupbox_layout.addWidget(self.save_button)
        tools_groupbox_layout.addWidget(self.refresh_button)

        self.create_item_button = QPushButton("Create Item")
        self.create_item_button.clicked.connect(self.create_item)
        tools_groupbox_layout.addWidget(self.create_item_button)

        self.delete_item_button = QPushButton("Delete Item")
        self.delete_item_button.clicked.connect(self.delete_items)
        tools_groupbox_layout.addWidget(self.delete_item_button)

        self.set_all_minGreaterAffix_button = QPushButton("Set all minGreaterAffix")
        self.set_all_minPower_button = QPushButton("Set all minPower")
        self.set_all_minCount_button = QPushButton("Set all minCount")
        self.set_all_minGreaterAffix_button.clicked.connect(self.set_all_minGreaterAffix)
        self.set_all_minPower_button.clicked.connect(self.set_all_minPower)
        self.set_all_minCount_button.clicked.connect(self.set_all_minCount)
        tools_groupbox_layout.addWidget(self.set_all_minGreaterAffix_button)
        tools_groupbox_layout.addWidget(self.set_all_minPower_button)
        tools_groupbox_layout.addWidget(self.set_all_minCount_button)
        tools_groupbox.setLayout(tools_groupbox_layout)
        info_layout.addWidget(tools_groupbox)
        self.main_layout.addLayout(info_layout)

        self.itemTypes = None
        with open(str(BASE_DIR / "assets/lang/enUS/item_types.json")) as f:
            self.itemTypes = json.load(f)

        self.affixesNames = None
        with open(str(BASE_DIR / "assets/lang/enUS/affixes.json")) as f:
            self.affixesNames = json.load(f)

        self.item_widgets = QWidget()
        self.item_widgets_layout = QGridLayout()
        self.item_widgets_layout.setDefaultPositioning(4, Qt.Orientation.Horizontal)
        self.item_list: list[D4LFItem] = []
        self.item_widgets.setLayout(self.item_widgets_layout)
        scrollable_layout.addWidget(self.item_widgets)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(scroll_area)
        instructions_label = QLabel("Instructions")
        self.main_layout.addWidget(instructions_label)

        instructions_text = QTextBrowser()
        instructions_text.append("You load a profile by clicking the 'File' button.")
        instructions_text.append("")
        instructions_text.append("All values are not saved automatically immediately upon changing.")
        instructions_text.append("You must click the save button to apply the changes to the profile.")
        instructions_text.append("")

        instructions_text.setFixedHeight(150)
        self.main_layout.addWidget(instructions_text)
        self.setLayout(self.main_layout)
        self.load()

    def confirm_discard_changes(self):
        reply = QMessageBox.warning(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save them before continuing?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.save_yaml()
            return True
        return reply == QMessageBox.StandardButton.No

    def create_alert(self, msg: str):
        reply = QMessageBox.warning(self, "Alert", msg, QMessageBox.StandardButton.Ok)
        return reply == QMessageBox.StandardButton.Ok

    def set_all_minGreaterAffix(self):
        if self.file_path:
            dialog = MinGreaterDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                minGreaterAffix = dialog.get_value()
                for d4lf_item in self.item_list:
                    d4lf_item.set_minGreaterAffix(minGreaterAffix)
        else:
            self.create_alert("No file loaded")

    def set_all_minCount(self):
        if self.file_path:
            dialog = MinCountDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                minCount = dialog.get_value()
                for d4lf_item in self.item_list:
                    d4lf_item.set_minCount(minCount)
        else:
            self.create_alert("No file loaded")

    def set_all_minPower(self):
        if self.file_path:
            dialog = MinPowerDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                minPower = dialog.get_value()
                for d4lf_item in self.item_list:
                    d4lf_item.set_minPower(minPower)
        else:
            self.create_alert("No file loaded")

    def load_items(self):
        row = 0
        col = 0

        while self.item_widgets_layout.count():
            item = self.item_widgets_layout.takeAt(0)
            item.widget().deleteLater()

        self.item_list = []
        for item in self.root.Affixes:
            d4lf_item = D4LFItem(item, self.affixesNames, self.itemTypes)
            self.item_list.append(d4lf_item)
            if col % 4 == 0 and col != 0:
                col = 0
                row += 1
            self.item_widgets_layout.addWidget(d4lf_item, row, col)
            col += 1

    def load(self):
        profiles: list[str] = IniConfigLoader().general.profiles
        custom_profile_path = IniConfigLoader().user_dir / "profiles"
        if not self.file_path:  # at start, set default file to build in params.ini
            if profiles[0]:
                custom_file_path = custom_profile_path / f"{profiles[0]}.yaml"
                if custom_file_path.is_file():
                    file_path = custom_file_path
                else:
                    file_path = None
                    LOGGER.error(f"Could not load profile {profiles[0]}. Checked: {custom_file_path}")
            else:
                file_path, _ = QFileDialog.getOpenFileName(self, "Open YAML File", str(custom_profile_path), "YAML Files (*.yaml *.yml)")
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open YAML File", str(custom_profile_path), "YAML Files (*.yaml *.yml)")

        if file_path:
            self.file_path = file_path
            if not self.load_yaml():
                return False
            self.update_filename_label()
            self.load_items()
            return True
        return False

    def load_yaml(self):
        filename = os.path.basename(self.file_path)  # Get the filename from the full path
        filename_without_extension = filename.rsplit(".", 1)[0]  # Remove the extension
        profile_str = filename_without_extension.replace("_", " ")  # Replace underscores with spaces
        self.root = None
        with open(self.file_path, encoding="utf-8") as f:
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
            except ValidationError as e:
                LOGGER.error(f"Validation errors in {self.file_path}")
                LOGGER.error(e)
                return False
        return True

    def update_filename_label(self):
        if self.file_path:
            filename = os.path.basename(self.file_path)  # Get the filename from the full path
            filename_without_extension = filename.rsplit(".", 1)[0]  # Remove the extension
            display_name = filename_without_extension.replace("_", " ")  # Replace underscores with spaces
            self.filenameLabel.setText(display_name)

    def save_yaml(self):
        new_profile_affixes = [d4lf_item.save_item() for d4lf_item in self.item_list]
        if self.root:
            p = ProfileModel(name="imported profile", Affixes=new_profile_affixes, Uniques=self.root.Uniques)
            save_as_profile(self.filenameLabel.text(), p, "custom")

    def check_close_save(self):
        new_profile_affixes = [d4lf_item.save_item_create() for d4lf_item in self.item_list]
        if self.root:
            p = ProfileModel(name=self.filenameLabel.text(), Affixes=new_profile_affixes, Uniques=self.root.Uniques)
            if p != self.root:
                return self.confirm_discard_changes()
        return True

    def check_item_name(self, name):
        return all(d4lf_item.item_name != name for d4lf_item in self.item_list)

    def create_item(self):
        dialog = CreateItem(self.itemTypes, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_value()
            if not self.check_item_name(list(item.root.keys())[0]):
                self.create_alert("An item with the same already exists, please choose a different name.")
                return
            item_widget = D4LFItem(item, self.affixesNames, self.itemTypes)
            item_widget.item_changed()
            self.item_list.append(item_widget)
            nb_item = self.item_widgets_layout.count()
            row = nb_item // 4
            col = nb_item % 4
            self.item_widgets_layout.addWidget(item_widget, row, col)
            return

    def delete_items(self):
        item_names = [item.item_name for item in self.item_list]
        dialog = DeleteItem(item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for item_name in dialog.get_value():
                for i, item in enumerate(self.item_list):
                    if item.item_name == item_name:
                        self.item_list.pop(i)
                        to_delete = self.item_widgets_layout.takeAt(i)
                        to_delete.widget().deleteLater()
                        break
            return

    def refresh(self):
        self.item_list = []

        if not self.load_yaml():
            return

        self.update_filename_label()
        self.load_items()
