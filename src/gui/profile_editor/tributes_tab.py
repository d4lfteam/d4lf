from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config.models import ItemRarity, TributeFilterModel
from src.dataloader import Dataloader
from src.gui.collapsible_widget import Container
from src.gui.dialog import CreateTribute, IgnoreScrollWheelComboBox, RemoveTribute

TRIBUTES_TABNAME = "Tributes"


class RarityWidget(QWidget):
    rarity_changed = pyqtSignal(ItemRarity, ItemRarity)

    def __init__(self, rarity: ItemRarity, parent=None):
        super().__init__(parent)
        self.rarity = rarity
        widget_layout = QHBoxLayout()
        widget_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name_combo = IgnoreScrollWheelComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.addItems(sorted(ItemRarity._member_names_))
        self.name_combo.setMinimumWidth(200)
        self.name_combo.setCurrentText(self.rarity.name)
        self.name_combo.currentIndexChanged.connect(self.update_rarity)
        widget_layout.addWidget(self.name_combo)
        self.setLayout(widget_layout)

    def update_rarity(self):
        old_rarity = self.rarity
        self.rarity = ItemRarity(ItemRarity._member_map_[self.name_combo.currentText()])
        self.rarity_changed.emit(old_rarity, self.rarity)


class TributeWidget(Container):
    tribute_name_changed = pyqtSignal()

    def __init__(self, tribute: TributeFilterModel):
        super().__init__(None, True)
        self.tribute = tribute
        if self.tribute.name:
            self.header.set_name(Dataloader().tribute_dict[self.tribute.name])
        self.old_name = None
        self.setup_ui()

    def setup_ui(self):
        container_layout = QVBoxLayout(self.contentWidget)
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        form_layout = QFormLayout()
        self.tribute_name_combo = IgnoreScrollWheelComboBox()
        self.tribute_name_combo.setEditable(True)
        self.tribute_name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.tribute_name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.tribute_name_combo.addItems(sorted(Dataloader().tribute_dict.values()))
        if self.tribute.name:
            self.tribute_name_combo.setCurrentText(Dataloader().tribute_dict[self.tribute.name])
        self.tribute_name_combo.setMaximumWidth(250)
        self.tribute_name_combo.currentIndexChanged.connect(self.update_tribute_name)
        self.first_changed_bug = True
        form_layout.addRow("Tribute:", self.tribute_name_combo)

        comparison_label = QLabel("Rarities")
        title_layout.addSpacing(50)
        title_layout.addWidget(comparison_label)
        self.rarity_list = QListWidget()
        self.rarity_list.setMinimumHeight(50)
        self.rarity_list.setAlternatingRowColors(True)
        for rarity in self.tribute.rarities:
            self.add_rarity_to_list(ItemRarity(rarity))

        condition_btn_layout = QHBoxLayout()
        add_condition_btn = QPushButton("Add Rarity")
        add_condition_btn.clicked.connect(self.add_rarity)
        condition_btn_layout.addWidget(add_condition_btn)
        remove_condition_btn = QPushButton("Remove Rarity")
        remove_condition_btn.clicked.connect(self.remove_selected)
        condition_btn_layout.addWidget(remove_condition_btn)
        layout.addLayout(form_layout)
        layout.addLayout(condition_btn_layout)
        layout.addLayout(title_layout)
        layout.addWidget(self.rarity_list)
        widget.setLayout(layout)
        container_layout.addWidget(widget)

    def add_rarity_to_list(self, item_rarity: ItemRarity):
        widget_item = QListWidgetItem()
        widget = RarityWidget(item_rarity)
        widget.rarity_changed.connect(self.on_rarity_update)
        widget_item.setSizeHint(widget.sizeHint())
        self.rarity_list.addItem(widget_item)
        self.rarity_list.setItemWidget(widget_item, widget)

    def add_rarity(self):
        item_rarity = ItemRarity(ItemRarity.Common)
        self.add_rarity_to_list(item_rarity)
        self.tribute.rarities.append(item_rarity)

    def remove_selected(self):
        for item in self.rarity_list.selectedItems():
            row = self.rarity_list.row(item)
            self.rarity_list.takeItem(row)
            self.tribute.rarities.pop(row)

    def revert_tribute_name(self):
        self.tribute_name_combo.currentIndexChanged.disconnect()
        self.tribute_name_combo.currentTextChanged.connect(lambda: self.update_tribute_name(False))
        self.tribute_name_combo.setCurrentText(self.old_name)
        self.tribute_name_combo.currentTextChanged.disconnect()
        self.tribute_name_combo.currentIndexChanged.connect(self.update_tribute_name)

    def update_tribute_name(self, classic=True):
        if self.first_changed_bug and self.tribute.name is not None and self.old_name is not None:
            self.first_changed_bug = False
            return
        new_name = self.tribute_name_combo.currentText()
        self.old_name = self.tribute.name
        self.header.set_name(new_name)
        reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
        self.tribute.name = reverse_dict.get(new_name)
        if classic:
            self.tribute_name_changed.emit()

    def on_rarity_update(self, old_rarity, rarity: ItemRarity):
        index = self.tribute.rarities.index(old_rarity)
        self.tribute.rarities.pop(index)
        self.tribute.rarities.insert(index, rarity)


class TributesTab(QWidget):
    def __init__(self, tributes: list[TributeFilterModel], parent=None):
        super().__init__(parent)
        if tributes is None:
            self.tributes = [TributeFilterModel()]
        else:
            self.tributes = tributes
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.create_button_layout()
        self.tribute_layout = QVBoxLayout()
        self.tributes_names = []
        for tribute in self.tributes:
            self.add_tribute(tribute)
            self.tributes_names.append(tribute.name)
        self.main_layout.addLayout(self.tribute_layout)

    def add_tribute(self, tribute_filter: TributeFilterModel):
        tribute_widget = TributeWidget(tribute_filter)
        tribute_widget.tribute_name_changed.connect(lambda: self.on_tribute_changed(tribute_widget))
        self.tribute_layout.addWidget(tribute_widget)

    def create_button_layout(self):
        btn_layout = QHBoxLayout()

        add_tribute_btn = QPushButton("Add Tribute")
        add_tribute_btn.clicked.connect(self.create_tribute)

        remove_tribute_btn = QPushButton("Remove Tribute")
        remove_tribute_btn.clicked.connect(self.remove_tribute)

        btn_layout.addWidget(add_tribute_btn)
        btn_layout.addWidget(remove_tribute_btn)
        self.main_layout.addLayout(btn_layout)

    def create_tribute(self):
        dialog = CreateTribute(self.tributes_names)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tribute_filter = dialog.get_value()
            self.add_tribute(tribute_filter)
            self.tributes.append(tribute_filter)
            self.tributes_names.append(tribute_filter.name)

    def remove_tribute(self):
        dialog = RemoveTribute(self.tributes_names)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tribute_to_delete = dialog.get_value()
            for tribute in tribute_to_delete:
                self.tributes_names.remove(tribute)
            to_delete_list = []
            for i in range(self.tribute_layout.count()):
                tribute_widget: TributeWidget = self.tribute_layout.itemAt(i).widget()
                if tribute_widget.tribute.name in tribute_to_delete:
                    to_delete_list.append(tribute_widget)
            for tribute_widget in to_delete_list:
                tribute_widget.setParent(None)
                self.tributes.remove(tribute_widget.tribute)

    def on_tribute_changed(self, tribute_widget: TributeWidget):
        new_name = tribute_widget.tribute.name
        old_name = tribute_widget.old_name
        if new_name in self.tributes_names:
            QMessageBox.warning(self, "Warning", f"Tribute {new_name} already exists. You can modify the existing one.")
            tribute_widget.revert_tribute_name()
            return
        if old_name in self.tributes_names:
            index = self.tributes_names.index(old_name)
            self.tributes_names.pop(index)
            self.tributes_names.insert(index, new_name)
