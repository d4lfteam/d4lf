from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import GlobalUniqueModel
from src.gui.dialog import DeleteItem, IgnoreScrollWheelSpinBox, MinGreaterDialog, MinPercentDialog, MinPowerDialog

UNIQUES_TABNAME = "Uniques"


class UniqueWidget(QWidget):
    def __init__(self, unique_model: GlobalUniqueModel, parent=None):
        super().__init__(parent)
        self.unique_model = unique_model

        self.setup_ui()

    def setup_ui(self):
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.create_general_groupbox()

        scroll_area.setWidget(content_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(scroll_area)
        self.setLayout(self.main_layout)

    def create_general_groupbox(self):
        self.general_groupbox = QGroupBox()
        self.general_groupbox.setTitle("Global Unique Rule")
        self.general_form = QFormLayout()

        self.profile_alias = QLineEdit()
        self.profile_alias.setMaximumWidth(300)
        self.profile_alias.setText(self.unique_model.profileAlias)
        self.profile_alias.textChanged.connect(self.update_profile_alias)
        self.general_form.addRow("Profile Alias:", self.profile_alias)

        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setRange(0, 800)
        self.min_power.setValue(self.unique_model.minPower)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        self.general_form.addRow("Minimum Power:", self.min_power)

        self.min_greater = IgnoreScrollWheelSpinBox()
        self.min_greater.setRange(0, 4)
        self.min_greater.setValue(self.unique_model.minGreaterAffixCount)
        self.min_greater.setMaximumWidth(150)
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)
        self.general_form.addRow("Min Greater Affixes:", self.min_greater)

        self.min_percent = IgnoreScrollWheelSpinBox()
        self.min_percent.setRange(0, 100)
        self.min_percent.setValue(self.unique_model.minPercentOfAspect)
        self.min_percent.setMaximumWidth(150)
        self.min_percent.valueChanged.connect(self.update_min_percent)
        self.general_form.addRow("Min Percent of Aspect:", self.min_percent)

        self.general_groupbox.setLayout(self.general_form)
        self.content_layout.addWidget(self.general_groupbox)

    def update_profile_alias(self, value: str):
        self.unique_model.profileAlias = value.strip()

    def update_min_power(self):
        self.unique_model.minPower = self.min_power.value()

    def update_min_greater_affix(self):
        self.unique_model.minGreaterAffixCount = self.min_greater.value()

    def update_min_percent(self):
        self.unique_model.minPercentOfAspect = self.min_percent.value()


class UniquesTab(QWidget):
    def __init__(self, unique_model_list: list[GlobalUniqueModel], parent=None):
        super().__init__(parent)
        self.unique_model_list = unique_model_list
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        self.add_button = QToolButton()
        self.add_button.setText("+")
        self.add_button.clicked.connect(self.add_item_type)

        self.tab_widget.setCornerWidget(self.add_button)
        self.toolbar = QToolBar("MyToolBar", self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)
        for i, unique_model in enumerate(self.unique_model_list):
            group = UniqueWidget(unique_model)
            self.tab_widget.addTab(group, f"Unique Rule {i}")

        add_item_button = QPushButton("Create Rule")
        remove_item_button = QPushButton("Remove Rule")
        set_all_minGreaterAffix_button = QPushButton("Set all minGreaterAffix")
        set_all_minPercentOfAspect_button = QPushButton("Set all minPercentOfAspect")
        set_all_minPower_button = QPushButton("Set all minPower")
        add_item_button.clicked.connect(self.add_item_type)
        remove_item_button.clicked.connect(self.remove_item_type)
        set_all_minGreaterAffix_button.clicked.connect(self.set_all_minGreaterAffix)
        set_all_minPercentOfAspect_button.clicked.connect(self.set_all_minPercentOfAspect)
        set_all_minPower_button.clicked.connect(self.set_all_minPower)
        self.toolbar.addWidget(add_item_button)
        self.toolbar.addWidget(remove_item_button)
        self.toolbar.addWidget(set_all_minGreaterAffix_button)
        self.toolbar.addWidget(set_all_minPercentOfAspect_button)
        self.toolbar.addWidget(set_all_minPower_button)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        self.unique_model_list.pop(index)
        self.rename_tabs()

    def remove_item_type(self):
        dialog = DeleteItem([self.tab_widget.tabText(i) for i in range(self.tab_widget.count())], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            to_delete_index = [
                i for i in range(self.tab_widget.count()) if self.tab_widget.tabText(i) in item_names_to_delete
            ]
            to_delete_index.reverse()
            for index in to_delete_index:
                self.tab_widget.removeTab(index)
                self.unique_model_list.pop(index)
            self.rename_tabs()
            return

    def rename_tabs(self):
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabText(i, f"Unique Rule {i}")

    def add_item_type(self):
        unique_model = GlobalUniqueModel()
        group = UniqueWidget(unique_model)
        self.tab_widget.addTab(group, f"Unique Rule {self.tab_widget.count()}")
        self.unique_model_list.append(unique_model)

    def set_all_minGreaterAffix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minGreaterAffix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: UniqueWidget = self.tab_widget.widget(i)
                tab.min_greater.setValue(minGreaterAffix)
                tab.update_min_greater_affix()

    def set_all_minPercentOfAspect(self):
        dialog = MinPercentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minPercentOfAspect = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: UniqueWidget = self.tab_widget.widget(i)
                tab.min_percent.setValue(minPercentOfAspect)
                tab.update_min_percent()

    def set_all_minPower(self):
        dialog = MinPowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            minPower = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab: UniqueWidget = self.tab_widget.widget(i)
                tab.min_power.setValue(minPower)
                tab.update_min_power()
