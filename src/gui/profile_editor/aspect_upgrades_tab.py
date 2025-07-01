from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from src.gui.dialog import AddAspectUpgrade

ASPECT_UPGRADES_TABNAME = "Aspect Upgrades"


class AspectUpgradesTab(QWidget):
    def __init__(self, aspect_upgrades: list[str], parent=None):
        super().__init__(parent)
        self.aspect_upgrades = aspect_upgrades
        self.upgrade_list_widget = QListWidget()
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 20, 0, 20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        label = QLabel(
            "Add any legendary aspects you'd like to have favorited if an upgrade is found. See the readme on AspectUpgrades for more information."
        )
        main_layout.addWidget(label)
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)

        self.upgrade_list_widget.insertItems(0, self.aspect_upgrades)
        main_layout.addWidget(self.upgrade_list_widget)
        self.setLayout(main_layout)

    def create_button_layout(self) -> QHBoxLayout:
        btn_layout = QHBoxLayout()

        add_tribute_btn = QPushButton("Add Aspect")
        add_tribute_btn.clicked.connect(self.add_aspect)

        remove_tribute_btn = QPushButton("Remove Aspect")
        remove_tribute_btn.clicked.connect(self.remove_aspect)

        btn_layout.addWidget(add_tribute_btn)
        btn_layout.addWidget(remove_tribute_btn)
        return btn_layout

    def add_aspect(self):
        dialog = AddAspectUpgrade(self.aspect_upgrades)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            aspect_upgrade = dialog.get_value()
            self.aspect_upgrades.append(aspect_upgrade)
            self.upgrade_list_widget.addItem(aspect_upgrade)

    def remove_aspect(self):
        current_aspect = self.upgrade_list_widget.currentItem().text()
        self.aspect_upgrades.remove(current_aspect)
        self.upgrade_list_widget.takeItem(self.upgrade_list_widget.currentRow())
