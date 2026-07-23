from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton, QTabWidget, QToolBar, QVBoxLayout, QWidget

from src.profiles.affix.dialogs import CreateItem
from src.profiles.affix.group import AffixGroupEditor
from src.profiles.editor import DeleteItem, MinGreaterDialog, MinPercentDialog, MinPowerDialog

if TYPE_CHECKING:
    from src.profiles import DynamicItemFilterModel

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class AffixesTab(QWidget):
    def __init__(self, affixes_model: list[DynamicItemFilterModel], parent=None):
        super().__init__(parent)
        self.affixes_model = affixes_model
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        """Populate the grid layout with existing groups."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.toolbar = QToolBar("MyToolBar", self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)

        self.item_names = []
        for affix_group in self.affixes_model:
            for item_name in affix_group.root:
                if item_name in self.item_names:
                    QMessageBox.warning(
                        self, "Warning", f"Item name already exist please rename {item_name} in the profile file."
                    )
                    continue
                group = AffixGroupEditor(affix_group)
                self.item_names.append(item_name)
                self.tab_widget.addTab(group, item_name)

        add_item_button = QPushButton()
        add_item_button.setText("Create Item")
        add_item_button.clicked.connect(self.add_item_type)

        remove_item_button = QPushButton()
        remove_item_button.setText("Remove Item")
        remove_item_button.clicked.connect(self.remove_item_type)

        set_all_min_greater_affix_button = QPushButton("Set All Min GAs (Excludes Auto Synced Items)")
        convert_all_to_min_percent_button = QPushButton("Convert All To Min %")
        set_all_min_power_button = QPushButton("Set all minPower")
        set_all_min_greater_affix_button.clicked.connect(self.set_all_min_greater_affix)
        convert_all_to_min_percent_button.clicked.connect(self.convert_all_to_min_percent_of_affix)
        set_all_min_power_button.clicked.connect(self.set_all_min_power)

        self.toolbar.addWidget(add_item_button)
        self.toolbar.addWidget(remove_item_button)
        self.toolbar.addWidget(set_all_min_greater_affix_button)
        self.toolbar.addWidget(convert_all_to_min_percent_button)
        self.toolbar.addWidget(set_all_min_power_button)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    def show_message(self, text):
        QMessageBox.information(self, "Info", text)

    def add_item_type(self):
        dialog = CreateItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_value()
            for item_name in item.root:
                group = AffixGroupEditor(item)
                self.item_names.append(item_name)
                self.tab_widget.addTab(group, item_name)
                self.affixes_model.append(item)
            return

    def close_tab(self, index):
        self.item_names.pop(index)
        self.tab_widget.removeTab(index)
        self.affixes_model.pop(index)

    def remove_item_type(self):
        dialog = DeleteItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            for item_name in item_names_to_delete:
                index = self.item_names.index(item_name)
                self.item_names.remove(item_name)
                self.tab_widget.removeTab(index)
                self.affixes_model.pop(index)
            return

    def set_all_min_greater_affix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_greater_affix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if not isinstance(tab, AffixGroupEditor) or tab.auto_sync_checkbox.isChecked():
                    continue
                tab.min_greater.setValue(min_greater_affix)
                tab.update_min_greater_affix()

    def convert_all_to_min_percent_of_affix(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, AffixGroupEditor):
            dialog = MinPercentDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                current_tab.convert_all_to_min_percent_of_affix(dialog.get_value())

    def set_all_min_power(self):
        dialog = MinPowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_power = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if not isinstance(tab, AffixGroupEditor):
                    continue
                tab.min_power.setValue(min_power)
                tab.update_min_power()
