from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QFrame, QGroupBox, QLineEdit, QScrollArea, QToolButton, QVBoxLayout, QWidget

from src.config.profile_models import GlobalUniqueModel
from src.gui.importer.gui_common import MAX_POWER
from src.gui.models.dialog import IgnoreScrollWheelSpinBox
from src.gui.models.tab_group_widget import TabGroupWidget

UNIQUES_TABNAME = "GlobalUniques"


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
        self.profile_alias.setText(self.unique_model.profile_alias)
        self.profile_alias.textChanged.connect(self.update_profile_alias)
        self.general_form.addRow("Profile Alias:", self.profile_alias)

        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setRange(0, MAX_POWER)
        self.min_power.setValue(self.unique_model.min_power)
        self.min_power.setMaximumWidth(150)
        self.min_power.valueChanged.connect(self.update_min_power)
        self.general_form.addRow("Minimum Power:", self.min_power)

        self.min_greater = IgnoreScrollWheelSpinBox()
        self.min_greater.setRange(0, 4)
        self.min_greater.setValue(self.unique_model.min_greater_affix_count)
        self.min_greater.setMaximumWidth(150)
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)
        self.general_form.addRow("Min Greater Affixes:", self.min_greater)

        self.min_percent = IgnoreScrollWheelSpinBox()
        self.min_percent.setRange(0, 100)
        self.min_percent.setValue(self.unique_model.min_percent_of_aspect)
        self.min_percent.setMaximumWidth(150)
        self.min_percent.valueChanged.connect(self.update_min_percent)
        self.general_form.addRow("Min Percent of Aspect:", self.min_percent)

        self.general_groupbox.setLayout(self.general_form)
        self.content_layout.addWidget(self.general_groupbox)

    def update_profile_alias(self, value: str):
        self.unique_model.profile_alias = value.strip()

    def update_min_power(self):
        self.unique_model.min_power = self.min_power.value()

    def update_min_greater_affix(self):
        self.unique_model.min_greater_affix_count = self.min_greater.value()

    def update_min_percent(self):
        self.unique_model.min_percent_of_aspect = self.min_percent.value()


class UniquesTab(TabGroupWidget):
    def __init__(self, unique_model_list: list[GlobalUniqueModel], parent=None):
        super().__init__(unique_model_list, parent)

    def toolbar_name(self) -> str:
        return "MyToolBar"

    def corner_widget(self) -> QToolButton:
        add_button = QToolButton()
        add_button.setText("+")
        add_button.clicked.connect(self.add_item)
        return add_button

    def create_editor(self, model: GlobalUniqueModel) -> UniqueWidget:
        return UniqueWidget(model)

    def tab_label(self, model: GlobalUniqueModel, index: int) -> str:
        return f"Unique Rule {index}"

    def create_model(self) -> GlobalUniqueModel:
        return GlobalUniqueModel()

    def add_button_text(self) -> str:
        return "Create Rule"

    def remove_button_text(self) -> str:
        return "Remove Rule"

    def after_models_changed(self):
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabText(i, f"Unique Rule {i}")
