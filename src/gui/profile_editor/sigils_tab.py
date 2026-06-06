from typing import override

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import SigilConditionModel, SigilFilterModel, SigilPriority
from src.dataloader import Dataloader
from src.gui.models.dialog import IgnoreScrollWheelComboBox
from src.gui.profile_editor.affixes_tab import (
    SelectionDialog,
    TruncatingComboBox,
    _create_column_header,
    _create_delete_btn,
    _create_summary_card_style,
)

SIGILS_TABNAME = "Sigils"


class SigilSummaryWidget(QWidget):
    delete_requested = pyqtSignal()
    config_changed = pyqtSignal()

    def __init__(self, model: SigilConditionModel, whitelist: bool, parent=None):
        super().__init__(parent)
        self.model = model
        self.whitelist = whitelist
        self.setObjectName("SummaryCard")
        self.setStyleSheet(_create_summary_card_style())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name = Dataloader().affix_sigil_dict_all["dungeons"].get(self.model.name, self.model.name)
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-weight: bold; color: #e2e8f0;")
        text_layout.addWidget(self.name_label)

        # Build condition summary
        cond_text = "No conditions"
        if self.model.condition:
            names = [Dataloader().affix_sigil_dict.get(c, c) for c in self.model.condition if c]
            cond_text = ", ".join(names)

        self.cond_label = QLabel(cond_text)
        self.cond_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.cond_label.setWordWrap(True)
        text_layout.addWidget(self.cond_label)

        self.main_layout.addLayout(text_layout, 1)

        self.delete_btn = _create_delete_btn()
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        self.main_layout.addWidget(self.delete_btn)

    @override
    def mousePressEvent(self, event):
        if event is None or event.button() == Qt.MouseButton.LeftButton:
            self.open_config_dialog()

    def open_config_dialog(self):
        name = Dataloader().affix_sigil_dict_all["dungeons"].get(self.model.name, self.model.name)
        dialog = SigilEditDialog(self, self.model, name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_display()
            self.config_changed.emit()

    def refresh_display(self):
        name = Dataloader().affix_sigil_dict_all["dungeons"].get(self.model.name, self.model.name)
        self.name_label.setText(name)

        cond_text = "No conditions"
        if self.model.condition:
            names = [Dataloader().affix_sigil_dict.get(c, c) for c in self.model.condition if c]
            cond_text = ", ".join(names)
        self.cond_label.setText(cond_text)


class SigilEditDialog(QDialog):
    def __init__(self, parent: QWidget, model: SigilConditionModel, dungeon_name: str):
        super().__init__(parent)
        self.setWindowTitle("Configure Sigil Rule")
        self.setMinimumWidth(500)
        self.model = model

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_combo = TruncatingComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.addItems(sorted(Dataloader().affix_sigil_dict_all["dungeons"].values()))
        self.name_combo.setCurrentText(dungeon_name)
        form.addRow("Dungeon:", self.name_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel("Conditions (Must match ANY):"))
        self.cond_list = QListWidget()
        self.cond_list.setMinimumHeight(200)
        for cond in self.model.condition:
            if cond:
                self.cond_list.addItem(Dataloader().affix_sigil_dict.get(cond, cond))
        layout.addWidget(self.cond_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Add Condition")
        add_btn.clicked.connect(self._add_condition)
        remove_btn = QPushButton("− Remove Selected")
        remove_btn.clicked.connect(self._remove_condition)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_condition(self):
        affix_sigil_dict = {
            **Dataloader().affix_sigil_dict_all["minor"],
            **Dataloader().affix_sigil_dict_all["major"],
            **Dataloader().affix_sigil_dict_all["positive"],
        }
        items = sorted(affix_sigil_dict.values())
        dialog = SelectionDialog(self, "Select Condition", items)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            val = dialog.get_value()
            if val:
                # Avoid adding same condition multiple times in UI
                existing = [self.cond_list.item(i).text() for i in range(self.cond_list.count())]
                if val not in existing:
                    self.cond_list.addItem(val)

    def _remove_condition(self):
        for item in self.cond_list.selectedItems():
            self.cond_list.takeItem(self.cond_list.row(item))

    def save_and_accept(self):
        new_name = self.name_combo.currentText()
        reverse_dungeon = {v: k for k, v in Dataloader().affix_sigil_dict_all["dungeons"].items()}
        dungeon_id = reverse_dungeon.get(new_name)
        if not dungeon_id:
            QMessageBox.warning(self, "Warning", "Please select a valid dungeon from the list.")
            return

        self.model.name = dungeon_id

        reverse_cond = {v: k for k, v in Dataloader().affix_sigil_dict.items()}
        self.model.condition = []
        for i in range(self.cond_list.count()):
            text = self.cond_list.item(i).text()
            if key := reverse_cond.get(text):
                self.model.condition.append(key)
        self.accept()


class SigilsTab(QWidget):
    def __init__(self, sigil_model: SigilFilterModel, parent=None):
        super().__init__(parent)
        self.sigil_model = sigil_model
        self.loaded = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        """Populate the grid layout with existing groups."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 5, 0, 5)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. General Config
        self.create_general_groupbox()

        # 2. Columns Layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)

        def create_col(title, add_cb):
            col_widget = QWidget()
            col_layout = QVBoxLayout(col_widget)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(0)

            header = _create_column_header(title, add_cb)
            col_layout.addWidget(header)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.Panel)
            scroll.setStyleSheet("QScrollArea { border: 1px solid #3c3c3c; background-color: #121212; }")

            inner = QWidget()
            inner_layout = QVBoxLayout(inner)
            inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            scroll.setWidget(inner)

            col_layout.addWidget(scroll)
            return col_widget, inner_layout

        self.whitelist_col, self.whitelist_layout = create_col("Whitelist", self.add_whitelist_sigil)
        self.blacklist_col, self.blacklist_layout = create_col("Blacklist", self.add_blacklist_sigil)

        columns_layout.addWidget(self.whitelist_col)
        columns_layout.addWidget(self.blacklist_col)
        self.main_layout.addLayout(columns_layout)

        # 3. Init content
        self.init_sigils()

    def create_general_groupbox(self):
        group = QGroupBox("Sigil Filtering")
        form = QFormLayout(group)
        self.priority_combobox = IgnoreScrollWheelComboBox()
        self.priority_combobox.addItems(SigilPriority._member_names_)
        self.priority_combobox.setCurrentText(self.sigil_model.priority)
        self.priority_combobox.setMaximumWidth(150)
        self.priority_combobox.currentIndexChanged.connect(self.update_priority)
        form.addRow("Priority Mode:", self.priority_combobox)
        self.main_layout.addWidget(group)

    def init_sigils(self):
        for sigil in self.sigil_model.whitelist:
            self.add_sigil_widget(sigil, whitelist=True)
        for sigil in self.sigil_model.blacklist:
            self.add_sigil_widget(sigil, whitelist=False)

    def add_sigil_widget(self, model: SigilConditionModel, whitelist: bool):
        layout = self.whitelist_layout if whitelist else self.blacklist_layout
        widget = SigilSummaryWidget(model, whitelist)
        widget.delete_requested.connect(lambda: self.remove_sigil_item(widget, whitelist))
        layout.addWidget(widget)
        return widget

    def add_whitelist_sigil(self):
        self._create_new_sigil(whitelist=True)

    def add_blacklist_sigil(self):
        self._create_new_sigil(whitelist=False)

    def _create_new_sigil(self, whitelist: bool):
        # Default to first dungeon key available
        dungeon_key = next(iter(Dataloader().affix_sigil_dict_all["dungeons"].keys()))
        new_sigil = SigilConditionModel(name=dungeon_key, condition=[])

        if whitelist:
            self.sigil_model.whitelist.append(new_sigil)
        else:
            self.sigil_model.blacklist.append(new_sigil)

        self.add_sigil_widget(new_sigil, whitelist).open_config_dialog()

    def remove_sigil_item(self, widget: SigilSummaryWidget, whitelist: bool):
        model_list = self.sigil_model.whitelist if whitelist else self.sigil_model.blacklist
        if widget.model in model_list:
            model_list.remove(widget.model)
        widget.setParent(None)
        widget.deleteLater()

    def update_priority(self):
        self.sigil_model.priority = SigilPriority(self.priority_combobox.currentText())
