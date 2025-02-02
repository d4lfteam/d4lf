from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
)

from src.config.models import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel, ItemType
from src.gui.dialog import IgnoreScrollWheelComboBox, IgnoreScrollWheelSpinBox


class D4LFItem(QGroupBox):
    def __init__(self, item : DynamicItemFilterModel, affixesNames, itemTypes):
        super().__init__()
        self.item_name = list(item.root.keys())[0]
        self.item = item
        self.item_type = self.item.root[self.item_name].itemType[0].value
        self.affix_pool = self.item.root[self.item_name].affixPool
        self.inherent_pool = self.item.root[self.item_name].inherentPool
        self.min_power = self.item.root[self.item_name].minPower

        self.changed = False
        self.affixesNames = affixesNames
        self.itemTypes = itemTypes

        self.setTitle(self.item_name)
        self.setStyleSheet("QGroupBox {font-size: 10pt;} QLabel {font-size: 10pt;} IgnoreScrollWheelComboBox {font-size: 10pt;} IgnoreScrollWheelSpinBox {font-size: 10pt;}")
        self.setMaximumSize(300, 500)

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.form_layout = QFormLayout()

        self.item_type_label = QLabel("Item Type:")
        self.item_type_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.item_type_label_info = QLabel(self.find_item_from_value(self.item_type))
        self.item_type_label_info.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.form_layout.addRow(self.item_type_label, self.item_type_label_info)

        self.minPowerEdit = IgnoreScrollWheelSpinBox()
        self.minPowerEdit.setMaximum(800)
        self.minPowerEdit.setMaximumWidth(75)
        self.minPowerEdit.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.form_layout.addRow(QLabel("minPower:"), self.minPowerEdit)
        self.main_layout.addLayout(self.form_layout)
        self.affixListLayout = None
        self.inherentListLayout = None
        if self.affix_pool:
            self.affixes_label = QLabel("Affixes:")
            self.affixes_label.setMaximumSize(200, 50)
            self.affixes_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            self.main_layout.addWidget(self.affixes_label)
            self.affixListLayout = QVBoxLayout()
            self.main_layout.addLayout(self.affixListLayout)

        if self.inherent_pool:
            self.inherent_label = QLabel("Inherent:")
            self.inherent_label.setMaximumSize(200, 50)
            self.inherent_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            self.main_layout.addWidget(self.inherent_label)
            self.inherentListLayout = QVBoxLayout()
            self.main_layout.addLayout(self.inherentListLayout)

        self.load_item()
        self.setLayout(self.main_layout)

        self.minPowerEdit.valueChanged.connect(self.item_changed)

    def load_item(self):
        self.minPowerEdit.setValue(self.min_power)
        for pool in self.affix_pool:
            for affix in pool.count:
                affixComboBox = self.create_affix_combobox(affix.name)
                self.affixListLayout.addWidget(affixComboBox)
            if pool.minCount is not None and pool.minGreaterAffixCount is not None:
                layout = self.create_form_layout(pool.minCount, pool.minGreaterAffixCount)
                self.affixListLayout.addLayout(layout)

        for pool in self.inherent_pool:
            for affix in pool.count:
                affixComboBox = self.create_affix_combobox(affix.name)
                self.inherentListLayout.addWidget(affixComboBox)

    def create_affix_combobox(self, affix_name):
        affixComboBox = IgnoreScrollWheelComboBox()
        affixComboBox.setEditable(True)
        affixComboBox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        affixComboBox.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        table_view = QTableView()
        table_view.horizontalHeader().setVisible(False)
        table_view.verticalHeader().setVisible(False)
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        affixComboBox.setView(table_view)
        affixComboBox.addItems(self.affixesNames.values())
        for i, affixes in enumerate(self.affixesNames.values()):
            affixComboBox.setItemData(i, affixes, Qt.ItemDataRole.ToolTipRole)

        key_list = list(self.affixesNames.keys())
        try:
            idx = key_list.index(affix_name)
        except ValueError:
            self.create_alert(f"{affix_name} is not a valid affix.")
            return affixComboBox
        affixComboBox.setCurrentIndex(idx)
        affixComboBox.setMaximumWidth(250)
        affixComboBox.currentTextChanged.connect(self.item_changed)
        return affixComboBox

    def create_alert(self, msg: str):
        reply = QMessageBox.warning(self, "Alert", msg, QMessageBox.StandardButton.Ok)
        return reply == QMessageBox.StandardButton.Ok

    def create_form_layout(self, minCount, minGreaterAffixCount):
        ret = QFormLayout()
        mincount_label = QLabel("minCount:")
        mincount_spinBox = IgnoreScrollWheelSpinBox()
        mincount_spinBox.setMaximum(3)
        mincount_spinBox.setValue(minCount)
        mincount_spinBox.setMaximumWidth(60)
        mincount_spinBox.valueChanged.connect(self.item_changed)
        ret.addRow(mincount_label, mincount_spinBox)
        mingreater_label = QLabel("minGreaterAffixCount:")
        mingreater_spinBox = IgnoreScrollWheelSpinBox()
        mingreater_spinBox.setMaximum(3)
        mingreater_spinBox.setValue(minGreaterAffixCount)
        mingreater_spinBox.setMaximumWidth(60)
        mingreater_spinBox.valueChanged.connect(self.item_changed)
        ret.addRow(mingreater_label, mingreater_spinBox)
        return ret

    def set_minPower(self, minPower):
        self.minPowerEdit.setValue(minPower)

    def set_minGreaterAffix(self, minGreaterAffix):
        for i in range(self.affixListLayout.count()):
            layout = self.affixListLayout.itemAt(i).layout()
            if layout is not None and isinstance(layout, QFormLayout):
                layout.itemAt(3).widget().setValue(minGreaterAffix)

    def set_minCount(self, minCount):
        for i in range(self.affixListLayout.count()):
            layout = self.affixListLayout.itemAt(i).layout()
            if layout is not None and isinstance(layout, QFormLayout):
                layout.itemAt(1).widget().setValue(minCount)

    def find_affix_from_value(self, target_value):
        for key, value in self.affixesNames.items():
            if value == target_value:
                return key
        return None

    def find_item_from_value(self, target_value):
        for key, value in self.itemTypes.items():
            if value == target_value:
                return key
        return None

    def save_item(self):
        self.min_power = self.minPowerEdit.value()
        for pool in self.affix_pool:
            for i in range(self.affixListLayout.count()):
                widget = self.affixListLayout.itemAt(i).widget()
                layout = self.affixListLayout.itemAt(i).layout()
                if widget is not None:
                    if isinstance(widget, IgnoreScrollWheelComboBox):
                        pool.count[i] = AffixFilterModel(name=self.find_affix_from_value(widget.currentText()))
                elif layout is not None and isinstance(layout, QFormLayout):
                    pool.minCount = layout.itemAt(1).widget().value()
                    pool.minGreaterAffixCount = layout.itemAt(3).widget().value()

        for pool in self.inherent_pool:
            for i in range(self.inherentListLayout.count()):
                widget = self.inherentListLayout.itemAt(i).widget()
                if isinstance(widget, IgnoreScrollWheelComboBox):
                    pool.count[i] = AffixFilterModel(name=self.find_affix_from_value(widget.currentText()))
        self.changed = False
        self.item.root[self.item_name].affixPool = self.affix_pool
        if self.inherent_pool:
            self.item.root[self.item_name].inherentPool = self.inherent_pool
        self.item.root[self.item_name].minPower= self.min_power
        return self.item

    def save_item_create(self):
        new_item = ItemFilterModel()
        new_item.itemType = [ItemType(self.item_type)]
        new_item.minPower = self.minPowerEdit.value()
        new_item.affixPool = []
        new_item.inherentPool = []
        affix_filter_count_list = []
        minCount = 0
        minGreaterAffixCount = 0

        for i in range(self.affixListLayout.count()):
                widget = self.affixListLayout.itemAt(i).widget()
                layout = self.affixListLayout.itemAt(i).layout()
                if widget is not None:
                    if isinstance(widget, IgnoreScrollWheelComboBox):
                        affix_filter_count_list.append(AffixFilterModel(name=self.find_affix_from_value(widget.currentText())))
                elif layout is not None and isinstance(layout, QFormLayout):
                    minCount = layout.itemAt(1).widget().value()
                    minGreaterAffixCount = layout.itemAt(3).widget().value()
        affix_filter_count = AffixFilterCountModel(minCount=minCount, minGreaterAffixCount=minGreaterAffixCount, count=affix_filter_count_list)
        new_item.affixPool.append(affix_filter_count)

        if self.inherentListLayout:
            inherent_filter_count_list = []
            for i in range(self.inherentListLayout.count()):
                widget = self.inherentListLayout.itemAt(i).widget()
                if isinstance(widget, IgnoreScrollWheelComboBox):
                    inherent_filter_count_list.append(AffixFilterModel(name=self.find_affix_from_value(widget.currentText())))
            inherent_filter_count = AffixFilterCountModel(count=inherent_filter_count_list)
            new_item.inherentPool.append(inherent_filter_count)

        return DynamicItemFilterModel(**{self.item_name: new_item})

    def item_changed(self):
        self.changed = True

    def has_changes(self):
        return self.changed
