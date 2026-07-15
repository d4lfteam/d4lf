from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING, TypeVar, override

from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
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

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicItemFilterModel,
    DynamicSealFilterModel,
    ItemFilterModel,
    ItemRarity,
    SealFilterModel,
    TributeFilterModel,
)
from src.dataloader import Dataloader
from src.gui.importer.gui_common import MAX_POWER
from src.gui.settings_tab import IgnoreScrollWheelComboBox
from src.item import SIGIL_RULE_TARGET_TYPES, ItemType, SigilRules, SigilRuleTargetType

if TYPE_CHECKING:
    from PyQt6.QtGui import QCloseEvent, QWheelEvent

OptionT = TypeVar("OptionT", bound=Hashable)


def _selected_sigil_target_type(combo: QComboBox) -> SigilRuleTargetType:
    target_type = combo.currentText()
    if target_type == "dungeon":
        return "dungeon"
    if target_type == "affix":
        return "affix"
    msg = f"Unknown sigil rule target type: {target_type}"
    raise ValueError(msg)


class IgnoreScrollWheelSpinBox(QSpinBox):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @override
    def wheelEvent(self, e: QWheelEvent | None) -> None:
        if self.hasFocus():
            super().wheelEvent(e)
            return

        if e is not None:
            e.ignore()


class MinPowerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Power")
        self.setFixedSize(250, 150)
        self.main_layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.label = QLabel("Min Power:")
        self.spinBox = IgnoreScrollWheelSpinBox()
        self.spinBox.setRange(0, MAX_POWER)
        self.spinBox.setValue(MAX_POWER)
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
        self.spinBox.setRange(0, 4)
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


class MinPercentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Percent Of Affix")
        self.setFixedSize(250, 150)
        self.main_layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.label = QLabel("Min Percent Of Affix:")
        self.spinBox = IgnoreScrollWheelSpinBox()
        self.spinBox.setRange(0, 100)
        self.spinBox.setValue(70)
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

    @override
    def accept(self) -> None:
        if not self.name_input.text():
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
        item.item_type = [item_type]
        item.affix_pool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=next(iter(Dataloader().affix_dict.keys()), ""))], min_count=2
            )
        ]
        item.min_power = 100
        return DynamicItemFilterModel(root={item_name: item})


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

        self.checkbox_list: list[QCheckBox] = []
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

        self.checkbox_list: list[QCheckBox] = []
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
        self.settings = QSettings("d4lf", "profile_editor")

        self.setWindowTitle("Create Sigil")
        self.setMinimumSize(420, 220)
        self.resize(self.settings.value("create_sigil_size", QSize(420, 220)))

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.kind_label = QLabel("Kind:")
        self.kind_input = IgnoreScrollWheelComboBox()
        self.kind_input.addItems(SIGIL_RULE_TARGET_TYPES)
        self.kind_input.currentTextChanged.connect(self._populate_names)

        self.name_label = QLabel("Name:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_input.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._populate_names()
        self.type_label = QLabel("Type: ")
        self.type_input = IgnoreScrollWheelComboBox()
        self.type_input.setEditable(True)
        self.type_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        type_completer = self.type_input.completer()
        if type_completer is not None:
            type_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.type_input.addItems(["whitelist", "blacklist"])
        self.form_layout.addRow(self.kind_label, self.kind_input)
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

    @override
    def accept(self) -> None:
        if self.type_input.currentText() == "whitelist" and self.name_input.currentText() in self.whitelist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            return
        if self.type_input.currentText() == "blacklist" and self.name_input.currentText() in self.blacklist_sigils:
            QMessageBox.warning(self, "Warning", "Sigil already exist in whitelist. You can modify the existing one.")
            return
        super().accept()

    def _populate_names(self):
        self.name_input.clear()
        targets = SigilRules.default().targets(_selected_sigil_target_type(self.kind_input))
        self.name_input.addItems([target.display for target in targets])

    def get_value(self):
        sigil_name = self.name_input.currentText()
        type_name = self.type_input.currentText()
        kind = _selected_sigil_target_type(self.kind_input)
        return sigil_name, type_name, kind

    @override
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.settings.setValue("create_sigil_size", self.size())
        if a0 is not None:
            a0.accept()


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

        self.checkbox_list: list[QCheckBox] = []
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
        name_completer = self.name_input.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
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

    @override
    def accept(self) -> None:
        reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
        tribute_name = reverse_dict.get(self.name_input.currentText())
        if tribute_name is None:
            QMessageBox.warning(self, "Warning", "Select a valid tribute from the list.")
            return
        if tribute_name in self.tributes:
            QMessageBox.warning(self, "Warning", "Tribute already exist. You can modify the existing one.")
            return
        super().accept()

    def get_value(self):
        reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
        tribute_name = reverse_dict.get(self.name_input.currentText())
        if tribute_name is None:
            msg = "Select a valid tribute from the list."
            raise ValueError(msg)
        return TributeFilterModel(name=[tribute_name], rarities=[])


class AddTributeRarity(QDialog):
    def __init__(self, rarities: list[ItemRarity], parent=None):
        super().__init__(parent)

        self.rarities = {ItemRarity(rarity) for rarity in rarities}

        self.setWindowTitle("Add Tribute Rarity")
        self.setFixedSize(300, 150)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.rarity_label = QLabel("Rarity:")
        self.rarity_input = IgnoreScrollWheelComboBox()
        self.rarity_input.setEditable(True)
        self.rarity_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        rarity_completer = self.rarity_input.completer()
        if rarity_completer is not None:
            rarity_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.rarity_input.addItems([rarity.name for rarity in ItemRarity])
        self.form_layout.addRow(self.rarity_label, self.rarity_input)
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

    @override
    def accept(self) -> None:
        rarity_name = self.rarity_input.currentText()
        if rarity_name not in ItemRarity.__members__:
            QMessageBox.warning(self, "Warning", "Select a valid rarity from the list.")
            return

        rarity = ItemRarity[rarity_name]
        if rarity in self.rarities:
            QMessageBox.warning(self, "Warning", "Rarity already exists in this tribute filter.")
            return

        super().accept()

    def get_value(self):
        rarity = ItemRarity[self.rarity_input.currentText()]
        return TributeFilterModel(name=[], rarities=[rarity])


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

        self.checkbox_list: list[QCheckBox] = []
        for tribute in self.tributes:
            checkbox = QCheckBox(str(Dataloader().tribute_dict[tribute])) if tribute else QCheckBox("None")
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


class AddAspectUpgrade(QDialog):
    def __init__(self, aspect_upgrades: list[str], parent=None):
        super().__init__(parent)

        self.aspect_upgrades = aspect_upgrades

        self.setWindowTitle("Add Aspect")
        self.setFixedSize(300, 150)

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        unchosen_aspect_ugprades = [x for x in Dataloader().aspect_list if x not in aspect_upgrades]

        self.name_label = QLabel("Aspect:")
        self.name_input = IgnoreScrollWheelComboBox()
        self.name_input.setEditable(True)
        self.name_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        name_completer = self.name_input.completer()
        if name_completer is not None:
            name_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_input.addItems(unchosen_aspect_ugprades)
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

    def get_value(self) -> str:
        return self.name_input.currentText()


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

        self.checkbox_list: list[QCheckBox] = []

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


def rarity_summary(rarities: list[ItemRarity]) -> str:
    if not rarities:
        return "All rarities"
    return ", ".join(r.value for r in rarities)


class CheckboxListDialog[OptionT](QDialog):
    """Generic multi-select checkbox dialog with an Ok/Cancel/Clear button row.

    Subclasses (or callers) supply the option list, current selection, and labels;
    this base handles checkbox creation, layout, clearing, and selection retrieval.
    """

    def __init__(
        self,
        parent: QWidget,
        window_title: str,
        group_title: str,
        options: list[OptionT],
        selected: list[OptionT],
        note_text: str,
        option_text: Callable[[OptionT], str] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.checkboxes: dict[OptionT, QCheckBox] = {}

        selected_set = set(selected)

        layout = QVBoxLayout(self)

        group_box = QGroupBox(group_title)
        group_layout = QVBoxLayout(group_box)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for option in options:
            checkbox = QCheckBox(option_text(option) if option_text is not None else str(option))
            checkbox.setChecked(option in selected_set)
            self.checkboxes[option] = checkbox
            content_layout.addWidget(checkbox)

        scroll_area.setWidget(content_widget)
        group_layout.addWidget(scroll_area)
        layout.addWidget(group_box)

        note_label = QLabel(note_text)
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        clear_button = button_box.addButton("Clear", QDialogButtonBox.ButtonRole.ResetRole)
        if clear_button is not None:
            clear_button.clicked.connect(self.clear_selection)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def clear_selection(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected(self) -> list[OptionT]:
        return [option for option, checkbox in self.checkboxes.items() if checkbox.isChecked()]


class RarityPicker(CheckboxListDialog[ItemRarity]):
    def __init__(self, parent: QWidget, selected_rarities: list[ItemRarity]):
        super().__init__(
            parent,
            window_title="Select Rarities",
            group_title="Rarities",
            options=list(ItemRarity),
            selected=selected_rarities,
            note_text="If no rarities are selected, all rarities will be kept for this filter.",
            option_text=lambda rarity: rarity.value,
        )

    def get_selected_rarities(self) -> list[ItemRarity]:
        return self.get_selected()


class CreateCharmOrSeal(QDialog):
    """Dialog for creating a new named charm or seal filter."""

    def __init__(self, item_list: list[str], is_charm: bool = True, parent=None):
        super().__init__(parent)
        self.is_charm = is_charm
        label = "Charm" if is_charm else "Seal"
        self.setWindowTitle(f"Create {label}")
        self.setFixedSize(300, 150)

        self.item_list = item_list

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.name_label = QLabel(f"{label} Name:")
        self.name_input = QLineEdit()
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

    @override
    def accept(self) -> None:
        if not self.name_input.text():
            QMessageBox.warning(self, "Warning", "Name cannot be empty")
            return
        if self.name_input.text() in self.item_list:
            QMessageBox.warning(self, "Warning", "Name already exists")
            return
        super().accept()

    def get_value(self):
        item_name = self.name_input.text()
        affix_dict = Dataloader().charm_affix_dict if self.is_charm else Dataloader().seal_affix_dict
        default_affix_name = next(iter(affix_dict.keys()), "")
        default_affix = AffixFilterModel(name=default_affix_name, value=None)
        default_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)

        if self.is_charm:
            config = CharmFilterModel(affix_pool=[default_pool])
            return DynamicCharmFilterModel(root={item_name: config})
        config = SealFilterModel(affix_pool=[default_pool])
        return DynamicSealFilterModel(root={item_name: config})


class SetPicker(CheckboxListDialog[str]):
    """Multi-select dialog for charm set names."""

    def __init__(self, parent: QWidget, selected_sets: list[str]):
        super().__init__(
            parent,
            window_title="Select Sets",
            group_title="Sets",
            options=sorted(Dataloader().set_list),
            selected=selected_sets,
            note_text="Select which sets this charm filter should match.",
        )

    def get_selected_sets(self) -> list[str]:
        return self.get_selected()
