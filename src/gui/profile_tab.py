import configparser
import sys
import os
import json
import time
from src.gui.build_from_yaml import *
from src.gui.dialog import *
from src.gui.d4lfitem import *
from src.config import BASE_DIR

PROFILE_TABNAME = "Edit Profile"

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
        self.file_button.clicked.connect(self.load_yaml)
        self.save_button.clicked.connect(self.save_yaml)
        tools_groupbox_layout.addWidget(self.file_button)
        tools_groupbox_layout.addWidget(self.save_button)

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
        with open(str(BASE_DIR / "assets/lang/enUS/item_types.json"), 'r') as f:
            self.itemTypes = json.load(f)

        self.affixesNames = None
        with open(str(BASE_DIR / "assets/lang/enUS/affixes.json"), 'r') as f:
            self.affixesNames = json.load(f)

        self.item_widgets = QWidget()
        self.item_widgets_layout = QGridLayout()
        self.item_list = []
        self.item_widgets.setLayout(self.item_widgets_layout)
        scrollable_layout.addWidget(self.item_widgets)
        self.update_filename_label()
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(scroll_area)
        instructions_label = QLabel("Instructions")
        self.main_layout.addWidget(instructions_label)

        instructions_text = QTextBrowser()
        instructions_text.append("The default profile loaded is the first profile in the params.ini file. You can change the default profile in the params.ini file by changing the 'profiles' value to the desired profile name.")
        instructions_text.append("You can also load a profile by clicking the 'File' button.")
        instructions_text.append("")
        instructions_text.append("All values are not saved automatically immediately upon changing.")
        instructions_text.append("You must click the save button to apply the changes to the profile.")
        instructions_text.append("")
        instructions_text.append("Note: You will need to restart d4lf after modifying these values. Modifying profile file manually while this gui is running is not supported (and really not necessary).")

        instructions_text.setFixedHeight(150)
        self.main_layout.addWidget(instructions_text)
        self.setLayout(self.main_layout)


    def confirm_discard_changes(self):
        reply = QMessageBox.warning(self, 'Unsaved Changes',
            "You have unsaved changes. Do you want to save them before continuing?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Yes:
            self.save_yaml()
            return True
        elif reply == QMessageBox.StandardButton.No:
            return True
        else:
            return False

    def create_alert(self, msg: str):
        reply = QMessageBox.warning(self, 'Alert', msg, QMessageBox.StandardButton.Ok)
        if reply == QMessageBox.StandardButton.Ok:
            return True
        else:
            return False

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
        i = 0
        j = 0

        while self.item_widgets_layout.count():
            item = self.item_widgets_layout.takeAt(0)
            item.widget().deleteLater()

        self.item_list = []

        for item in self.root.affixes:
            d4lf_item = D4LFItem(item, self.affixesNames, self.itemTypes)
            self.item_list.append(d4lf_item)
            if i % 4 == 0 and i != 0:
                i = 0
                j += 1
            self.item_widgets_layout.addWidget(d4lf_item, j, i)
            i += 1

    def load_yaml(self):
        if not self.file_path: # at start, set default file to build in params.ini
            params_file = os.path.join(os.getenv("USERPROFILE"), ".d4lf", "params.ini")
            params_data = configparser.ConfigParser()
            params_data.read(params_file)
            profile_names = params_data.get('general', 'profiles').split(',')
            if profile_names[0]:
                file_path = os.path.join(os.getenv("USERPROFILE"), ".d4lf", "profiles", f"{profile_names[0]}.yaml")
            else:
                base_dir = os.path.join(os.getenv("USERPROFILE"), ".d4lf", "profiles")
                file_path, _ = QFileDialog.getOpenFileName(self, "Open YAML File", base_dir, "YAML Files (*.yaml *.yml)")
        else:
            base_dir = os.path.join(os.getenv("USERPROFILE"), ".d4lf", "profiles")
            file_path, _ = QFileDialog.getOpenFileName(self, "Open YAML File", base_dir, "YAML Files (*.yaml *.yml)")
        if file_path:
            self.root = Root.load_yaml(file_path)
            self.file_path = os.path.abspath(file_path)
            self.update_filename_label()
            self.load_items()
            return True
        return False

    def update_filename_label(self, close=False):
        if close:
            self.filenameLabel.setText("No file loaded")
            return
        if not self.file_path:
            if not self.load_yaml():
                self.filenameLabel.setText("No file loaded")
                return

        if self.file_path:
            filename = self.file_path.split("\\")[-1]  # Get the filename from the full path
            filename_without_extension = filename.rsplit(".", 1)[0]  # Remove the extension
            display_name = filename_without_extension.replace("_", " ")  # Replace underscores with spaces
            self.filenameLabel.setText(display_name)

    def save_yaml(self):
        for d4lf_item in self.item_list:
            d4lf_item.save_item()
        if self.root:
            self.root.save_yaml(self.file_path)

    def check_close_save(self):
        if self.item_list:
            for d4lf_item in self.item_list:
                if d4lf_item.has_changes():
                    return self.confirm_discard_changes()