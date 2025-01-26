from src.gui.build_from_yaml import *
from PyQt6.QtWidgets import QHeaderView, QTableView, QLabel, QVBoxLayout, QHBoxLayout, QSpinBox, QComboBox, QGroupBox, QSizePolicy, QFormLayout, QCompleter, QMessageBox
from PyQt6.QtCore import Qt

class D4LFItem(QGroupBox):
    def __init__(self, item : Item, affixesNames, itemTypes):
        super().__init__()
        self.setTitle(item.itemName)
        self.setStyleSheet("QGroupBox {font-size: 10pt;} QLabel {font-size: 10pt;} QComboBox {font-size: 10pt;} QSpinBox {font-size: 10pt;}")
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.item = item
        self.changed = False
        self.setMaximumSize(300, 500)
        self.affixesNames = affixesNames
        self.itemTypes = itemTypes

        self.minPowerEdit = QSpinBox(self)
        self.minPowerEdit.setMaximum(800)
        self.minPowerEdit.setMaximumWidth(100)
        self.minPowerEdit.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.minPower_form = QFormLayout()
        self.minPower_form.addRow(QLabel("minPower:"), self.minPowerEdit)
        self.main_layout.addLayout(self.minPower_form)

        if item.affixPool:
            self.affixes_label = QLabel("Affixes:")
            self.affixes_label.setMaximumSize(200, 50)
            self.affixes_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            self.main_layout.addWidget(self.affixes_label)
            self.affixListLayout = QVBoxLayout()
            self.main_layout.addLayout(self.affixListLayout)

        if item.inherentPool:
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
        self.minPowerEdit.setValue(self.item.minPower)
        for pool in self.item.affixPool:
            for affix in pool.count:
                affixComboBox = self.create_affix_combobox(affix.name)
                self.affixListLayout.addWidget(affixComboBox)
            if pool.minCount != None:
                minCount = self.create_pair_label_spinbox("minCount:", 3, pool.minCount)
                self.affixListLayout.addLayout(minCount)
            if pool.minGreaterAffixCount != None:
                minGreaterAffixCount = self.create_pair_label_spinbox("minGreaterAffixCount:", 3, pool.minGreaterAffixCount)
                self.affixListLayout.addLayout(minGreaterAffixCount)

        for pool in self.item.inherentPool:
            for affix in pool.count:
                affixComboBox = self.create_affix_combobox(affix.name)
                self.inherentListLayout.addWidget(affixComboBox)

    def create_affix_combobox(self, affix_name):
        affixComboBox = QComboBox()
        affixComboBox.setEditable(True)
        affixComboBox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        affixComboBox.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        table_view = QTableView()
        table_view.horizontalHeader().setVisible(False)
        table_view.verticalHeader().setVisible(False)
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        affixComboBox.setView(table_view)
        affixComboBox.addItems(self.affixesNames.values())

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
        reply = QMessageBox.warning(self, 'Alert', msg, QMessageBox.StandardButton.Ok)
        if reply == QMessageBox.StandardButton.Ok:
            return True
        else:
            return False

    def create_pair_label_spinbox(self, labelText, maxValue, value):
        ret = QHBoxLayout()
        ret.setContentsMargins(0, 0, 50, 0)
        label = QLabel(labelText)
        spinBox = QSpinBox()
        spinBox.setMaximum(maxValue)
        spinBox.setValue(value)
        spinBox.setMaximumWidth(70)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        spinBox.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ret.addWidget(label)
        ret.addWidget(spinBox)
        spinBox.valueChanged.connect(self.item_changed)
        return ret

    def set_minPower(self, minPower):
        self.minPowerEdit.setValue(minPower)

    def set_minGreaterAffix(self, minGreaterAffix):
        for i in range(self.affixListLayout.count()):
            layout = self.affixListLayout.itemAt(i).layout()
            if layout != None:
                if isinstance(layout, QHBoxLayout):
                    if layout.itemAt(0).widget().text() == "minGreaterAffixCount:":
                        layout.itemAt(1).widget().setValue(minGreaterAffix)

    def set_minCount(self, minCount):
        for i in range(self.affixListLayout.count()):
            layout = self.affixListLayout.itemAt(i).layout()
            if layout != None:
                if isinstance(layout, QHBoxLayout):
                    if layout.itemAt(0).widget().text() == "minCount:":
                        layout.itemAt(1).widget().setValue(minCount)

    def find_key_from_value(self, target_value):
        for key, value in self.affixesNames.items():
            if value == target_value:
                return key
        return None

    def save_item(self):
        self.item.minPower = self.minPowerEdit.value()
        for pool in self.item.affixPool:
            for i in range(self.affixListLayout.count()):
                widget = self.affixListLayout.itemAt(i).widget()
                layout = self.affixListLayout.itemAt(i).layout()
                if widget != None:
                    if isinstance(widget, QComboBox):
                        pool.count[i] = Affix(self.find_key_from_value(widget.currentText()))
                elif layout != None:
                    if isinstance(layout, QHBoxLayout):
                        if layout.itemAt(0).widget().text() == "minCount:":
                            pool.minCount = layout.itemAt(1).widget().value()
                        elif layout.itemAt(0).widget().text() == "minGreaterAffixCount:":
                            pool.minGreaterAffixCount = layout.itemAt(1).widget().value()

        for pool in self.item.inherentPool:
            for i in range(self.inherentListLayout.count()):
                widget = self.inherentListLayout.itemAt(i).widget()
                if isinstance(widget, QComboBox):
                    pool.count[i] = Affix(self.find_key_from_value(widget.currentText()))
        self.changed = False

    def item_changed(self):
        self.changed = True

    def has_changes(self):
        return self.changed