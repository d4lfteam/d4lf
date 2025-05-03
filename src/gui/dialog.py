from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config.models import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel, ItemType, TributeFilterModel
from src.dataloader import Dataloader
from src.gui.config_tab import IgnoreScrollWheelComboBox


class IgnoreScrollWheelSpinBox(QSpinBox):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            return QSpinBox.wheelEvent(self, event)

        return event.ignore()


class MinPowerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Power")
        self.setFixedSize(250, 150)
        self.main_layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.label = QLabel("Min Power:")
        self.spinBox = IgnoreScrollWheelSpinBox()
        self.spinBox.setRange(0, 800)
        self.spinBox.setValue(800)
        self.form_layout.addRow(self.label, self.spinBox)
        self.main_layout.addLayout(self.form_layout)

        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.buttonLayout)
        self.setLayout(self.main_layout)

    def get_value(self):
        return self.spinBox.value()


class MinGreaterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Greater Affix")
        self.setFixedSize(250, 150)
        self.main_layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.label = QLabel("Min Greater Affix:")
        self.spinBox = IgnoreScrollWheelSpinBox()
        self.spinBox.setRange(0, 3)
        self.spinBox.setValue(0)
        self.form_layout.addRow(self.label, self.spinBox)
        self.main_layout.addLayout(self.form_layout)

        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.buttonLayout)
        self.setLayout(self.main_layout)

    def get_value(self):
        return self.spinBox.value()


class CreateItem(QDialog):
    def __init__(self, item_list: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Item")
        self.setFixedSize(300, 150)
        self.main_layout = QVBoxLayout()

        self.form_layout = QFormLayout()

        self.name_label = QLabel("Item Name:")
        self.name_input = QLineEdit()
        self.form_layout.addRow(self.name_label, self.name_input)
        self.item_list = item_list
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def accept(self):
        if self.name_input.text() == "":
            QMessageBox.warning(self, "Warning", "Item name cannot be empty")
            return
        if self.name_input.text() in self.item_list:
            QMessageBox.warning(self, "Warning", "Item name already exist")
            return
        super().accept()

    def get_value(self):
        item_name = self.name_input.text()
        item_type = ItemType.Amulet

        item = ItemFilterModel()
        item.itemType = [item_type]
        item.affixPool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=list(Dataloader().affix_dict.keys())[0])],
                minCount=2,
                minGreaterAffixCount=0,
            )
        ]
        item.minPower = 100
        return DynamicItemFilterModel(**{item_name: item})


class DeleteItem(QDialog):
    def __init__(self, item_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete Items")
        self.setFixedSize(300, 200)
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.groupbox = QGroupBox("Items")
        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select items to delete:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list = []
        for name in item_names:
            checkbox = QCheckBox(name)
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def get_value(self):
        return [checkbox.text() for checkbox in self.checkbox_list if checkbox.isChecked()]


class DeleteAffixPool(QDialog):
    def __init__(self, nb_affix_pool, inherent: bool = False, parent=None):
        super().__init__(parent)
        if inherent:
            self.setWindowTitle("Delete Inherent Pool")
            self.groupbox = QGroupBox("Inherent Pool")
        else:
            self.setWindowTitle("Delete Affix Pool")
            self.groupbox = QGroupBox("Affix Pool")
        self.setFixedSize(300, 200)
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select items to delete:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list = []
        for i in range(nb_affix_pool):
            checkbox = QCheckBox(f"Count {i}")
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def get_value(self):
        return [checkbox.text() for checkbox in self.checkbox_list if checkbox.isChecked()]


class CreateSigil(QDialog):
    def __init__(self, whitelist_sigils: list[str], blacklist_sigils: list[str], parent=None):
        super().__init__(parent)

        self.whitelist_sigils = whitelist_sigils
        self.blacklist_sigils = blacklist_sigils

        self.setWindowTitle("Create Sigil")
        self.setFixedSize(300, 150)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_label = QLabel("Dungeon:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_input.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_input.addItems(sorted(Dataloader().affix_sigil_dict_all["dungeons"].values()))
        self.type_label = QLabel("Type: ")
        self.type_input = IgnoreScrollWheelComboBox()
        self.type_input.setEditable(True)
        self.type_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.type_input.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.type_input.addItems(["whitelist", "blacklist"])
        self.form_layout.addRow(self.name_label, self.name_input)
        self.form_layout.addRow(self.type_label, self.type_input)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def accept(self):
        if self.type_input.currentText() == "whitelist" and self.name_input.currentText() in self.whitelist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            return
        if self.type_input.currentText() == "blacklist" and self.name_input.currentText() in self.blacklist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            return
        super().accept()

    def get_value(self):
        sigil_name = self.name_input.currentText()
        type_name = self.type_input.currentText()
        return sigil_name, type_name


class RemoveSigil(QDialog):
    def __init__(self, sigils: list[str], blacklist: bool = False, parent=None):
        super().__init__(parent)
        self.sigils = sigils
        if blacklist:
            self.setWindowTitle("Delete Blacklist Sigil")
            self.groupbox = QGroupBox("Blacklist")
        else:
            self.setWindowTitle("Delete Whitelist Sigil")
            self.groupbox = QGroupBox("Whitelist")
        self.setFixedSize(300, 300)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select Sigils to delete:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list = []
        for sigil in self.sigils:
            checkbox = QCheckBox(sigil)
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def get_value(self):
        return [checkbox.text() for checkbox in self.checkbox_list if checkbox.isChecked()]


class CreateTribute(QDialog):
    def __init__(self, tributes: list[str], parent=None):
        super().__init__(parent)

        self.tributes = tributes

        self.setWindowTitle("Create Tribute")
        self.setFixedSize(300, 150)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_label = QLabel("Tribute:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_input.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_input.addItems(sorted(Dataloader().tribute_dict.values()))
        self.form_layout.addRow(self.name_label, self.name_input)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def accept(self):
        reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
        if reverse_dict.get(self.name_input.currentText()) in self.tributes:
            QMessageBox.warning(self, "Warning", "Tribute already exist. You can modify the existing one.")
            return
        super().accept()

    def get_value(self):
        reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
        tribute_name = reverse_dict.get(self.name_input.currentText())
        return TributeFilterModel(name=tribute_name, rarities=[])


class RemoveTribute(QDialog):
    def __init__(self, tributes: list[str], parent=None):
        super().__init__(parent)
        self.tributes = tributes
        self.setWindowTitle("Delete Tributes")
        self.groupbox = QGroupBox("Tributes")
        self.setFixedSize(300, 300)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area = QScrollArea(self)
        scroll_widget = QWidget(scroll_area)
        scrollable_layout = QVBoxLayout(scroll_widget)
        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select Tributes to delete:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list = []
        for tribute in self.tributes:
            if tribute:
                checkbox = QCheckBox(Dataloader().tribute_dict[tribute])
            else:
                checkbox = QCheckBox("None")
            scrollable_layout.addWidget(checkbox)
            self.checkbox_list.append(checkbox)
        scroll_widget.setLayout(scrollable_layout)
        scroll_area.setWidget(scroll_widget)
        self.groupbox_layout.addWidget(scroll_area)
        self.groupbox.setLayout(self.groupbox_layout)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def get_value(self):
        reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
        return [reverse_dict.get(checkbox.text()) for checkbox in self.checkbox_list if checkbox.isChecked()]


class CreateUnique(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Unique")
        self.groupbox = QGroupBox("Unique Infos")
        self.setFixedSize(300, 300)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.groupbox_layout = QVBoxLayout()

        label = QLabel("Select info to add to the Unique:")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.groupbox_layout.addWidget(label)

        self.checkbox_list = []

        checkbox_aspect = QCheckBox("Aspect")
        checkbox_affixe = QCheckBox("Affixes")
        self.groupbox_layout.addWidget(checkbox_aspect)
        self.groupbox_layout.addWidget(checkbox_affixe)
        self.checkbox_list.append(checkbox_aspect)
        self.checkbox_list.append(checkbox_affixe)

        self.groupbox.setLayout(self.groupbox_layout)
        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.main_layout.addWidget(self.groupbox)
        self.main_layout.addLayout(self.buttonLayout)

        self.setLayout(self.main_layout)

    def get_value(self):
        return [checkbox.text() for checkbox in self.checkbox_list if checkbox.isChecked()]
