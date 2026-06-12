import contextlib
import copy
import json
import logging
from pathlib import Path
from typing import override

from PyQt6.QtCore import QSettings, QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator, QIntValidator, QPainter
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
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    DynamicItemFilterModel,
    ItemFilterModel,
)
from src.dataloader import Dataloader
from src.gui.importer.gui_common import MAX_POWER
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox
from src.gui.models.dialog import (
    CreateItem,
    DeleteAffixPool,
    DeleteItem,
    IgnoreScrollWheelComboBox,
    IgnoreScrollWheelSpinBox,
    MinGreaterDialog,
    MinPercentDialog,
    MinPowerDialog,
)
from src.item.data.item_type import ItemType, is_weapon

LOGGER = logging.getLogger(__name__)

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"
MAX_DROPDOWN_TEXT_LENGTH = 50


class TruncatingComboBox(IgnoreScrollWheelComboBox):
    def __init__(self, max_length=MAX_DROPDOWN_TEXT_LENGTH, parent=None):
        super().__init__(parent)
        self.max_length = max_length

    @override
    def addItems(self, texts: list[str]):
        display_texts = [self._get_display_text(t) for t in texts]
        super().addItems(display_texts)
        for i, text in enumerate(texts):
            if len(text) > self.max_length:
                self.setItemData(i, text, Qt.ItemDataRole.ToolTipRole)

    @override
    def setCurrentText(self, text: str):
        super().setCurrentText(self._get_display_text(text))
        self.setToolTip(text if len(text) > self.max_length else "")

    def _get_display_text(self, text: str) -> str:
        if len(text) > self.max_length:
            return text[: self.max_length - 3] + "..."
        return text


class CharacterSpinBox(IgnoreScrollWheelSpinBox):
    value_changed = pyqtSignal(int)

    def __init__(self, value=0, min_val=0, max_val=100, step=1, parent=None):
        super().__init__()
        self.setRange(min_val, max_val)
        self.setValue(value)
        self.setSingleStep(step)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(26)
        self.valueChanged.connect(self.value_changed.emit)

    def set_value(self, val: int):
        self.setValue(val)

    def set_range(self, min_val: int, max_val: int):
        self.setRange(min_val, max_val)

    def set_minimum(self, val: int):
        self.setMinimum(val)

    def set_maximum(self, val: int):
        self.setMaximum(val)

    @override
    def setFixedWidth(self, w: int):
        super().setFixedWidth(w)


def _item_type_summary(item_types: list[ItemType]) -> str:
    if not item_types:
        return "All item types"
    return ", ".join(item_type.value for item_type in item_types)


def _get_affix_metadata() -> dict:
    """Helper to load affix metadata for slot filtering."""
    try:
        meta_path = Path("assets/lang/enUS/affix_metadata.json")
        if not meta_path.exists():
            LOGGER.warning(f"Affix metadata file not found: {meta_path}")
            return {}
        with meta_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        LOGGER.error(f"Error decoding affix metadata JSON from {meta_path}: {e}")
    except OSError as e:
        LOGGER.error(f"Error reading affix metadata file {meta_path}: {e}")
    return {}


class ItemTypePicker(QDialog):
    def __init__(self, parent: QWidget, item_types: list[ItemType], selected_item_types: list[ItemType]):
        super().__init__(parent)
        self.setWindowTitle("Select Item Types")
        self.resize(650, 500)
        self.checkboxes: dict[ItemType, CheckmarkCheckBox] = {}

        selected_item_type_set = set(selected_item_types)
        weapon_item_types = [
            item_type for item_type in item_types if is_weapon(item_type) or item_type == ItemType.Shield
        ]
        weapon_item_type_set = set(weapon_item_types)
        non_weapon_item_types = [item_type for item_type in item_types if item_type not in weapon_item_type_set]

        layout = QVBoxLayout(self)
        picker_layout = QHBoxLayout()
        picker_layout.addWidget(self._create_item_type_group("Weapons", weapon_item_types, selected_item_type_set))
        picker_layout.addWidget(
            self._create_item_type_group("Non-weapons", non_weapon_item_types, selected_item_type_set)
        )
        layout.addLayout(picker_layout)

        note_label = QLabel("If no item types are selected, all item types will be evaluated for this filter.")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        clear_button = button_box.addButton("Clear", QDialogButtonBox.ButtonRole.ResetRole)
        clear_button.clicked.connect(self.clear_selection)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_item_type_group(
        self, title: str, item_types: list[ItemType], selected_item_types: set[ItemType]
    ) -> QGroupBox:
        group_box = QGroupBox(title)
        group_layout = QVBoxLayout(group_box)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for item_type in item_types:
            checkbox = CheckmarkCheckBox(item_type.value)
            checkbox.setChecked(item_type in selected_item_types)
            self.checkboxes[item_type] = checkbox
            content_layout.addWidget(checkbox)

        scroll_area.setWidget(content_widget)
        group_layout.addWidget(scroll_area)
        return group_box

    def clear_selection(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_item_types(self) -> list[ItemType]:
        return [item_type for item_type, checkbox in self.checkboxes.items() if checkbox.isChecked()]


class SelectionDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, items: list[str]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 500)
        layout = QVBoxLayout(self)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter items...")
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.addItems(items)
        layout.addWidget(self.list_widget)

        self.search_input.textChanged.connect(self._filter_list)
        self.list_widget.itemDoubleClicked.connect(self.accept)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _filter_list(self, text: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def get_value(self) -> str | None:
        selected = self.list_widget.selectedItems()
        return selected[0].text() if selected else None


def _create_delete_btn() -> QPushButton:
    btn = QPushButton("−")
    btn.setFixedWidth(30)
    btn.setToolTip("Remove this entry")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton {
            color: #ef4444;
            font-weight: bold;
            font-size: 16px;
            border: 1px solid #450a0a;
            background-color: #1a0a0a;
        }
        QPushButton:hover { background-color: #450a0a; color: white; }
    """)
    return btn


def _affix_summary(pool: AffixFilterCountModel) -> str:
    names = []
    for a in pool.count:
        name = Dataloader().affix_dict.get(a.name, a.name)
        if getattr(a, "required", False):
            name = f'<span style="color: #ef4444;">[REQ]</span> {name}'
        if a.want_greater:
            name += " (GA)"
        names.append(name)
    return "<br>".join(names)


def _affix_card_summary(model: AffixFilterModel) -> str:
    name = Dataloader().affix_dict.get(model.name, model.name)
    if getattr(model, "required", False):
        name = f"[REQ] {name}"
    if model.want_greater:
        name += " (GA)"
    return name


def _create_summary_card_style() -> str:
    return """
        QWidget#SummaryCard {
            border: 1px solid #2d2d2d;
            border-left: 3px solid #3b82f6;
            border-radius: 4px;
            background-color: #1e1e1e;
            margin-bottom: 4px;
        }
        QWidget#SummaryCard:hover {
            background-color: #262626;
            border-color: #404040;
            border-left-color: #60a5fa;
        }
    """


def _create_column_header(title: str, add_callback: callable, remove_callback: callable | None = None) -> QWidget:
    header = QWidget()
    header.setObjectName("ColumnHeader")
    header.setStyleSheet(
        "QWidget#ColumnHeader { background-color: #1e3a5f; border-top-left-radius: 8px; border-top-right-radius: 8px; }"
    )
    layout = QHBoxLayout(header)
    layout.setContentsMargins(5, 5, 5, 5)

    if remove_callback:
        btn = _create_delete_btn()
        btn.clicked.connect(remove_callback)
        layout.addWidget(btn)
    else:
        layout.addSpacing(30)
    layout.addStretch()

    lbl = QLabel(title)
    lbl.setStyleSheet(
        "font-weight: bold; font-size: 15px; color: #e2e8f0; text-transform: uppercase; border: none; background: transparent;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)
    layout.addStretch()

    btn = QPushButton("+")
    btn.setFixedWidth(30)
    btn.setToolTip(f"Add to {title}")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton {
            color: #22c55e;
            font-weight: bold;
            font-size: 16px;
            border: 1px solid #064e3b;
            background-color: #06201b;
        }
        QPushButton:hover { background-color: #064e3b; color: white; }
    """)
    btn.clicked.connect(add_callback)
    layout.addWidget(btn)

    return header


def _create_column_footer(model: AffixFilterCountModel, on_change_cb: callable) -> QWidget:
    footer = QWidget()
    main_layout = QVBoxLayout(footer)
    main_layout.setContentsMargins(5, 5, 5, 5)
    main_layout.setSpacing(2)

    flavor_lbl = QLabel("Set the quantity of affixes wanted for a match.")
    flavor_lbl.setStyleSheet("color: #64748b; font-size: 12px; font-style: italic;")
    flavor_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(flavor_lbl)

    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    main_layout.addLayout(layout)

    layout.addStretch()

    min_lbl = QLabel("Min:")
    min_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
    layout.addWidget(min_lbl)

    min_spin = CharacterSpinBox()
    min_spin.set_range(0, 10)
    min_spin.setFixedWidth(100)
    min_spin.set_value(model.min_count)
    min_spin.value_changed.connect(lambda v: (setattr(model, "min_count", v), on_change_cb()))
    layout.addWidget(min_spin)

    max_lbl = QLabel("Max:")
    max_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
    layout.addWidget(max_lbl)

    max_spin = CharacterSpinBox()
    max_spin.set_range(0, 100)
    max_spin.setFixedWidth(100)
    max_spin.set_value(min(model.max_count, 100))
    max_spin.value_changed.connect(
        lambda v: (setattr(model, "max_count", v if v < 100 else 2147483647), on_change_cb())
    )
    layout.addWidget(max_spin)

    layout.addStretch()

    # Store references to update if model changes externally
    footer.setProperty("min_spin", min_spin)
    footer.setProperty("max_spin", max_spin)

    return footer


class UniqueAspectDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        model: AspectUniqueFilterModel,
        character_class: str = "all",
        allowed_item_types: list[ItemType] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configure Unique Aspect")
        self.setMinimumWidth(550)
        self.model = model
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; color: #e2e8f0; }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #09090b;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #e2e8f0;
                padding: 4px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #3b82f6; }
            QPushButton {
                background-color: #262626;
                border: 1px solid #3f3f46;
                color: #e2e8f0;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #323232; border-color: #52525b; }
        """)

        layout = QVBoxLayout(self)
        header = QLabel("Unique Aspect Configuration")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 5px;")
        layout.addWidget(header)

        desc = QLabel("Set the name and threshold value or percentage for this unique aspect.")
        desc.setStyleSheet("font-size: 12px; color: #94a3b8; font-style: italic; margin-bottom: 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()

        unique_dict = Dataloader().aspect_unique_dict
        filtered_uniques = []

        # Normalize class for internal lookup
        search_class = character_class.lower()
        if "warlock" in search_class:
            search_class = "sorcerer"

        for name, data in unique_dict.items():
            # Class Filter: Keep if item is for 'all' or matches the current class
            u_class = str(data.get("class", "all")).lower()
            if search_class != "all" and u_class not in ("all", search_class):
                continue

            # Slot Filter: Keep if item type matches any of the allowed types for this filter
            u_type = str(data.get("item_type"))
            if allowed_item_types and u_type and not any(u_type in (t.name, t.value) for t in allowed_item_types):
                continue

            filtered_uniques.append(name)

        if not filtered_uniques:
            filtered_uniques = list(unique_dict.keys())

        self.name_combo = TruncatingComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.addItems(sorted(filtered_uniques))
        if model.name in filtered_uniques:
            self.name_combo.setCurrentText(model.name)
        elif self.name_combo.count() > 0:
            self.name_combo.setCurrentIndex(0)
        form.addRow("Aspect:", self.name_combo)

        self.mode_combo = IgnoreScrollWheelComboBox()
        self.mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE if model.min_percent_of_aspect else AFFIX_VALUE_MODE)
        form.addRow("Mode:", self.mode_combo)

        self.value_edit = QLineEdit()
        if model.min_percent_of_aspect:
            self.value_edit.setText(str(model.min_percent_of_aspect))
        elif model.value is not None:
            self.value_edit.setText(str(model.value))
        form.addRow("Threshold:", self.value_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_and_accept(self):
        name = self.name_combo.currentText()
        if name in Dataloader().aspect_unique_dict:
            self.model.name = name

        mode = self.mode_combo.currentText()
        val_str = self.value_edit.text()

        if mode == AFFIX_PERCENT_MODE:
            try:
                self.model.min_percent_of_aspect = int(val_str) if val_str else 0
            except ValueError:
                self.model.min_percent_of_aspect = 0
            self.model.value = None
        else:
            try:
                self.model.value = float(val_str) if val_str else None
            except ValueError:
                self.model.value = None
            self.model.min_percent_of_aspect = 0
        self.accept()


class AffixEditDialog(QDialog):
    def __init__(self, parent: QWidget, model: AffixFilterModel, allowed_item_types: list[ItemType] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Configure Affix")
        self.setMinimumWidth(550)
        self.model = model
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; color: #e2e8f0; }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #09090b;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #e2e8f0;
                padding: 4px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #3b82f6; }
            QPushButton {
                background-color: #262626;
                border: 1px solid #3f3f46;
                color: #e2e8f0;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #323232; border-color: #52525b; }
        """)

        layout = QVBoxLayout(self)
        header = QLabel("Affix Configuration")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 5px;")
        layout.addWidget(header)

        desc = QLabel("Configure the properties, GA requirements, and thresholds for this affix.")
        desc.setStyleSheet("font-size: 12px; color: #94a3b8; font-style: italic; margin-bottom: 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()

        affix_dict = Dataloader().affix_dict
        filtered_affixes = sorted(affix_dict.values())

        self.name_combo = TruncatingComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_combo.addItems(filtered_affixes)
        if model.name in affix_dict:
            current_display = affix_dict[model.name]
            self.name_combo.setCurrentText(current_display)
        form.addRow("Affix:", self.name_combo)

        options_layout = QHBoxLayout()
        self.required_checkbox = CheckmarkCheckBox("Required")
        self.required_checkbox.setChecked(getattr(model, "required", False))
        self.greater_checkbox = CheckmarkCheckBox("GA")
        self.greater_checkbox.setChecked(model.want_greater)
        self.greater_checkbox.setProperty("greaterCheckbox", True)  # noqa: FBT003
        options_layout.addWidget(self.required_checkbox)
        options_layout.addWidget(self.greater_checkbox)
        options_layout.addStretch()
        form.addRow("Options:", options_layout)

        self.mode_combo = IgnoreScrollWheelComboBox()
        self.mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE if model.min_percent_of_affix else AFFIX_VALUE_MODE)
        form.addRow("Mode:", self.mode_combo)

        self.value_edit = QLineEdit()
        if model.min_percent_of_affix:
            self.value_edit.setText(str(model.min_percent_of_affix))
        elif model.value is not None:
            self.value_edit.setText(str(model.value))
        form.addRow("Threshold:", self.value_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_and_accept(self):
        reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
        affix_id = reverse_dict.get(self.name_combo.currentText())
        if affix_id:
            self.model.name = affix_id

        self.model.required = self.required_checkbox.isChecked()
        self.model.want_greater = self.greater_checkbox.isChecked()

        mode = self.mode_combo.currentText()
        val_str = self.value_edit.text()

        if mode == AFFIX_PERCENT_MODE:
            try:
                self.model.min_percent_of_affix = int(val_str) if val_str else 0
            except ValueError:
                self.model.min_percent_of_affix = 0
            self.model.value = None
        else:
            try:
                self.model.value = float(val_str) if val_str else None
            except ValueError:
                self.model.value = None
            self.model.min_percent_of_affix = 0
        self.accept()


class AffixPoolDialog(QDialog):
    def __init__(
        self, parent: QWidget, pool: AffixFilterCountModel, title: str, allowed_item_types: list[ItemType] | None = None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 600)
        self.pool = pool
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; color: #e2e8f0; }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #09090b;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #e2e8f0;
                padding: 4px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #3b82f6; }
            QPushButton {
                background-color: #262626;
                border: 1px solid #3f3f46;
                color: #e2e8f0;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #323232; border-color: #52525b; }
        """)

        layout = QVBoxLayout(self)
        header = QLabel(title)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 5px;")
        layout.addWidget(header)

        desc = QLabel("Manage the list of affixes in this pool and define how many matches are required.")
        desc.setStyleSheet("font-size: 12px; color: #94a3b8; font-style: italic; margin-bottom: 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        config_layout = QHBoxLayout()
        self.min_count = CharacterSpinBox()
        self.min_count.set_value(pool.min_count)
        self.min_count.setFixedWidth(100)

        self.max_count = CharacterSpinBox()
        self.max_count.set_value(min(pool.max_count, 2147483647))
        self.max_count.setFixedWidth(100)

        config_layout.addWidget(QLabel("Min:"))
        config_layout.addWidget(self.min_count)
        config_layout.addSpacing(20)
        config_layout.addWidget(QLabel("Max:"))
        config_layout.addWidget(self.max_count)
        config_layout.addStretch()
        layout.addLayout(config_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.viewport().setStyleSheet("background: transparent;")

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for affix in pool.count:
            self.add_affix_row(affix, allowed_item_types)

        scroll.setWidget(self.rows_container)
        layout.addWidget(scroll)

        add_btn = QPushButton("+ Add Affix to Pool")
        add_btn.clicked.connect(lambda: self.add_affix(allowed_item_types))
        layout.addWidget(add_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_affix_row(self, model: AffixFilterModel, allowed_item_types: list[ItemType] | None = None):
        widget = AffixWidget(model, allowed_item_types=allowed_item_types)
        widget.delete_requested.connect(lambda: self.remove_affix_widget(widget))
        self.rows_layout.addWidget(widget)

    def add_affix(self, allowed_item_types: list[ItemType] | None = None):
        affix_dict = Dataloader().affix_dict
        filtered_affixes = sorted(affix_dict.values())

        dialog = SelectionDialog(self, "Select Affix", filtered_affixes)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            val = dialog.get_value()
            if val:
                reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
                affix_id = reverse_dict.get(val)
                new_model = AffixFilterModel(name=affix_id, value=None)
                self.pool.count.append(new_model)
                self.add_affix_row(new_model, allowed_item_types)

    def remove_affix_widget(self, widget: AffixWidget):
        if widget.affix in self.pool.count:
            self.pool.count.remove(widget.affix)
        widget.setParent(None)
        widget.deleteLater()

    def save_and_accept(self):
        self.pool.min_count = self.min_count.value()
        self.pool.max_count = self.max_count.value()
        self.accept()


class AffixGroupEditor(QWidget):
    duplicate_requested = pyqtSignal(DynamicItemFilterModel)

    def __init__(self, dynamic_filter: DynamicItemFilterModel, parent=None):
        super().__init__(parent)
        self.settings = QSettings("d4lf", "profile_editor")
        self.affix_column_widgets = []
        self.affix_pool_layouts = []
        self.affix_footers = []
        self.dynamic_filter = dynamic_filter
        for item_name, config in dynamic_filter.root.items():
            self.item_name = item_name
            self.config = config

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        self.setup_ui()

    def setup_ui(self):
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(0, 10, 0, 0)

        # Row 1: Item Alias, Min Power, Duplicate Button
        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(0, 0, 0, 0)

        top_row_layout.addWidget(QLabel("Item Name / Alias:"))
        self.alias_edit = QLineEdit()
        self.alias_edit.setText(self.item_name)
        self.alias_edit.setStyleSheet("""
            QLineEdit {
                background-color: #09090b;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #e2e8f0;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """)
        self.alias_edit.setFixedWidth(200)
        self.alias_edit.textChanged.connect(self.update_item_alias)
        top_row_layout.addWidget(self.alias_edit)

        top_row_layout.addSpacing(30)

        top_row_layout.addWidget(QLabel("Minimum Power:"))
        self.min_power = IgnoreScrollWheelSpinBox()
        self.min_power.setMaximum(MAX_POWER)
        self.min_power.setValue(self.config.min_power)
        self.min_power.setFixedWidth(80)
        self.min_power.valueChanged.connect(self.update_min_power)
        top_row_layout.addWidget(self.min_power)

        top_row_layout.addStretch()

        duplicate_btn = QPushButton("Duplicate Item")
        duplicate_btn.setFixedWidth(120)
        duplicate_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a5f;
                border: 1px solid #3b82f6;
                color: #e2e8f0;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        duplicate_btn.clicked.connect(self._on_duplicate_clicked)
        top_row_layout.addWidget(duplicate_btn)

        self.content_layout.addLayout(top_row_layout)

        # Row 2: Min Greater Affixes, Auto Sync, Add Pool Button
        ga_row_layout = QHBoxLayout()
        ga_row_layout.setContentsMargins(0, 5, 0, 10)

        ga_row_layout.addWidget(QLabel("Min Greater Affixes:"))
        self.min_greater = CharacterSpinBox()
        self.min_greater.set_range(0, 4)
        self.min_greater.set_value(self.config.min_greater_affix_count)
        self.min_greater.setFixedWidth(100)
        self.min_greater.setToolTip(
            "Minimum number of checked affixes that must be Greater Affixes.\n"
            "0 = Accept items even without GAs (for leveling)\n"
            "1-4 = At least this many checked affixes must be GA"
        )
        self.min_greater.value_changed.connect(self.update_min_greater_affix_from_spin)

        self.auto_sync_checkbox = CheckmarkCheckBox("Auto Sync")
        self.auto_sync_checkbox.setToolTip(
            "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
            "When unchecked: You can manually set Min Greater Affixes to any value"
        )
        self.auto_sync_checkbox.setStyleSheet("background: transparent;")
        self.auto_sync_checkbox.setChecked(
            self.settings.value(f"auto_sync_ga_{self.item_name}", defaultValue=False, type=bool)
        )
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)

        self.greater_count_label = QLabel()
        self.greater_count_label.setProperty("greaterCountLabel", True)  # noqa: FBT003
        self._refresh_widget_style(self.greater_count_label)
        self.update_greater_count_label()

        ga_row_layout.addWidget(self.min_greater)
        ga_row_layout.addWidget(self.auto_sync_checkbox)
        ga_row_layout.addWidget(self.greater_count_label)
        ga_row_layout.addStretch()

        add_pool_btn = QPushButton("Add Additional Affix Pool")
        add_pool_btn.setFixedWidth(180)
        add_pool_btn.setStyleSheet("""
            QPushButton {
                background-color: #06201b;
                border: 1px solid #064e3b;
                color: #22c55e;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #064e3b; color: white; }
        """)
        add_pool_btn.clicked.connect(self.add_additional_affix_pool_column)
        ga_row_layout.addWidget(add_pool_btn)

        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())

        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setProperty("autoSyncSpin", True)  # noqa: FBT003
            self._refresh_widget_style(self.min_greater)

        self.content_layout.addLayout(ga_row_layout)

        # 3-Column Layout
        columns_layout = QHBoxLayout()
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(15)
        self.columns_layout = columns_layout

        # Column 1: Unique Aspects
        self.aspect_col, self.aspect_rows_layout, _ = self._create_col_helper("Unique Aspects", self.add_unique_aspect)
        columns_layout.addWidget(self.aspect_col)

        # Column(s) 2: Affix Pool(s)
        for pool in self.config.affix_pool:
            self._add_affix_pool_column_widget(pool)

        self.content_layout.addLayout(columns_layout)

        # Initialize content
        self.init_unique_aspects()
        self.init_affix_pool()

    def _on_duplicate_clicked(self):
        self.duplicate_requested.emit(self.dynamic_filter)

    def init_unique_aspects(self):
        for aspect in self.config.unique_aspect:
            self.add_unique_aspect_item(aspect)

    def init_affix_pool(self):
        for i, pool in enumerate(self.config.affix_pool):
            for affix in pool.count:
                self.add_affix_item(affix, pool_idx=i)

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def add_unique_aspect_item(self, model: AspectUniqueFilterModel):
        widget = UniqueAspectWidget(model)
        widget.delete_requested.connect(lambda: self.remove_unique_aspect_widget(widget))
        self.aspect_rows_layout.addWidget(widget)
        return widget

    def add_unique_aspect(self):
        aspect_name = next(iter(Dataloader().aspect_unique_dict.keys()))
        new_model = AspectUniqueFilterModel(name=aspect_name)
        self.config.unique_aspect.append(new_model)
        widget = self.add_unique_aspect_item(new_model)
        if widget.open_config_dialog() == QDialog.DialogCode.Rejected:
            self.remove_unique_aspect_widget(widget)

    def remove_unique_aspect_widget(self, widget: UniqueAspectWidget):
        if widget.unique_aspect in self.config.unique_aspect:
            self.config.unique_aspect.remove(widget.unique_aspect)
        widget.setParent(None)
        widget.deleteLater()

    def add_affix_item(self, model: AffixFilterModel, pool_idx: int = 0):
        layout = self.affix_pool_layouts[pool_idx]
        widget = AffixSummaryWidget(model)
        widget.delete_requested.connect(lambda: self.remove_affix_item_widget(widget, pool_idx))
        widget.config_changed.connect(self.update_greater_count_label)
        layout.addWidget(widget)
        return widget

    def remove_affix_item_widget(self, widget, pool_idx: int = 0):
        layout = self.affix_pool_layouts[pool_idx]
        pool = self.config.affix_pool[pool_idx]
        idx = layout.indexOf(widget)
        if idx != -1:
            pool.count.pop(idx)
            widget.setParent(None)
            widget.deleteLater()
            self.update_greater_count_label()

    def add_affix_to_pool(self, pool_model: AffixFilterCountModel):
        idx = self.config.affix_pool.index(pool_model)
        common_affixes = ["Energy", "Strength", "Dexterity", "Vitality", "Intelligence"]
        default_name = None
        reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
        for affix in common_affixes:
            if affix in reverse_dict:
                default_name = reverse_dict[affix]
                break
        if default_name is None:
            default_name = next(iter(Dataloader().affix_dict.keys()))

        default_affix = AffixFilterModel(name=default_name, value=None)
        pool_model.count.append(default_affix)
        widget = self.add_affix_item(default_affix, pool_idx=idx)
        if widget.open_config_dialog() == QDialog.DialogCode.Rejected:
            self.remove_affix_item_widget(widget, pool_idx=idx)

    def add_affix_pool(self):
        if self.config.affix_pool:
            self.add_affix_to_pool(self.config.affix_pool[0])

    def remove_selected(self, layout_widget: QVBoxLayout, inherent: bool = False):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool, inherent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            to_delete_list = []
            for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if item and item.widget() is not None and item.widget().header.name in to_delete:
                    to_delete_list.append((item.widget(), i))
            to_delete_list.reverse()
            for widget, index in to_delete_list:
                widget.setParent(None)
                if inherent:
                    self.config.inherent_pool.pop(index)
                else:
                    self.config.affix_pool.pop(index)
            self.reorganize_pool(layout_widget)

    def reorganize_pool(self, layout_widget: QVBoxLayout):
        pass

    def _create_col_helper(self, title, add_cb, pool_model=None, remove_cb=None):
        col_widget = QWidget()
        col_layout = QVBoxLayout(col_widget)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        header = _create_column_header(title, add_cb, remove_cb)
        col_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #2d2d2d; border-left: none; border-bottom: none; background-color: #121212; }"
        )

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(inner)
        col_layout.addWidget(scroll)

        footer = None
        if pool_model is not None:
            footer = _create_column_footer(pool_model, self.update_greater_count_label)
            footer.setStyleSheet(
                "background-color: #1a1a1a; border: 1px solid #2d2d2d; border-left: none; border-top: none;"
            )
            col_layout.addWidget(footer)

        return col_widget, inner_layout, footer

    def _add_affix_pool_column_widget(self, pool_model: AffixFilterCountModel):
        def add_cb():
            self.add_affix_to_pool(pool_model)

        # Only provide a remove callback for additional pools (index > 0)
        is_additional = self.config.affix_pool.index(pool_model) > 0
        remove_cb = (lambda: self.remove_affix_pool_column(pool_model)) if is_additional else None
        col_widget, inner_layout, footer = self._create_col_helper("Affix Pool", add_cb, pool_model, remove_cb)
        self.columns_layout.addWidget(col_widget)

        self.affix_column_widgets.append(col_widget)
        self.affix_pool_layouts.append(inner_layout)
        self.affix_footers.append(footer)

    def add_additional_affix_pool_column(self):
        new_pool = AffixFilterCountModel(count=[], min_count=1)
        self.config.affix_pool.append(new_pool)
        self._add_affix_pool_column_widget(new_pool)

    def remove_affix_pool_column(self, pool_model: AffixFilterCountModel):
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this entire affix pool?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            idx = self.config.affix_pool.index(pool_model)
            self.config.affix_pool.pop(idx)

            widget = self.affix_column_widgets.pop(idx)
            self.affix_pool_layouts.pop(idx)
            self.affix_footers.pop(idx)

            widget.setParent(None)
            widget.deleteLater()
            self.update_greater_count_label()

    def update_item_alias(self, new_name: str):
        new_name = new_name.strip()
        if not new_name or new_name == self.item_name:
            return

        if self.item_name in self.dynamic_filter.root:
            model = self.dynamic_filter.root.pop(self.item_name)
            self.dynamic_filter.root[new_name] = model

        old_name = self.item_name
        self.item_name = new_name

        p = self.parent()
        while p:
            if isinstance(p, AffixesTab):
                if old_name in p.item_names:
                    idx = p.item_names.index(old_name)
                    p.item_names[idx] = new_name
                    p.item_data_map.pop(old_name, None)
                    p.item_data_map[new_name] = self.dynamic_filter
                    p.tab_widget.setTabText(idx, new_name)
                break
            p = p.parent()

    def update_min_power(self):
        self.config.min_power = self.min_power.value()

    def update_min_greater_affix(self):
        self.config.min_greater_affix_count = self.min_greater.value()

    def update_min_greater_affix_from_spin(self, value):
        self.config.min_greater_affix_count = value

    def toggle_auto_sync(self):
        is_auto_sync = self.auto_sync_checkbox.isChecked()

        # Save UI-only state (replaces writing to config)
        self.settings.setValue(f"auto_sync_ga_{self.item_name}", is_auto_sync)

        # Keep your existing behavior
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            self.min_greater.setProperty("autoSyncSpin", True)  # noqa: FBT003
            self._refresh_widget_style(self.min_greater)
            count = self.count_want_greater_affixes()
            self.min_greater.set_value(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setProperty("autoSyncSpin", False)  # noqa: FBT003
            self._refresh_widget_style(self.min_greater)

        self.update_greater_count_label()

    def _update_auto_sync_count(self):
        count = self.count_want_greater_affixes()
        self.min_greater.set_value(count)
        self.update_greater_count_label()

    def sync_min_greater_from_checkboxes(self):
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.set_value(count)

    def iter_affix_widgets(self):
        # NOTE: Since AffixWidgets are now inside dialogs, we can't yield UI widgets for bulk updates.
        # Bulk operations in this view must be handled via direct model updates or a different pattern.
        return []

    def refresh_all_summaries(self):
        for layouts in [self.affix_pool_layouts]:
            for layout in layouts:
                for i in range(layout.count()):
                    w = layout.itemAt(i).widget()
                    if isinstance(w, AffixSummaryWidget):
                        w.refresh_display()
        for i in range(self.aspect_rows_layout.count()):
            w = self.aspect_rows_layout.itemAt(i).widget()
            if isinstance(w, UniqueAspectWidget):
                w.refresh_display()

    def count_want_greater_affixes(self):
        want_greater_count = 0

        for pool in self.config.affix_pool:
            for affix in pool.count:
                if affix.want_greater:
                    want_greater_count += 1

        return want_greater_count

    def update_greater_count_label(self):
        count = self.count_want_greater_affixes()
        if count == 0:
            self.greater_count_label.setText("(no greater affixes marked)")
        elif count == 1:
            self.greater_count_label.setText("(1 greater affix marked)")
        else:
            self.greater_count_label.setText(f"({count} greater affixes marked)")

        # Update affix pool footers
        for footer, model in zip(self.affix_footers, self.config.affix_pool, strict=False):
            self._update_footer_constraints(footer, model)

    def _update_footer_constraints(self, footer, model):
        if footer and model:
            min_spin = footer.property("min_spin")
            if min_spin:
                min_allowed = sum(1 for a in model.count if getattr(a, "required", False))
                min_spin.set_minimum(min_allowed)
                if model.min_count < min_allowed:
                    model.min_count = min_allowed
                    min_spin.set_value(min_allowed)

    def convert_all_to_min_percent_of_affix(self, percent: int):
        for affix_widget in self.iter_affix_widgets():
            affix_widget.set_min_percent(percent, convert_mode=True)


class UniqueAspectWidget(QWidget):
    delete_requested = pyqtSignal()
    config_changed = pyqtSignal()

    def __init__(self, unique_aspect: AspectUniqueFilterModel, parent=None):
        super().__init__(parent)
        self.unique_aspect = unique_aspect
        self.setObjectName("SummaryCard")
        self.setStyleSheet(_create_summary_card_style())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(22, 8, 10, 8)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; color: #e2e8f0;")
        self.main_layout.addWidget(self.summary_label, 1)

        self.threshold_label = QLabel()
        self.threshold_label.setMinimumWidth(60)
        self.threshold_label.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold;")
        self.main_layout.addWidget(self.threshold_label)

        self.delete_btn = _create_delete_btn()
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        self.main_layout.addWidget(self.delete_btn)

        self.refresh_display()

    @override
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        p.end()

    @override
    def mousePressEvent(self, event):
        if event is None or event.button() == Qt.MouseButton.LeftButton:
            self.open_config_dialog()

    def open_config_dialog(self) -> QDialog.DialogCode:
        # Gather context by crawling up the widget tree
        char_class = "all"
        allowed_types = []
        curr = self.parent()
        while curr:
            if hasattr(curr, "profile_model"):  # ProfileEditor
                char_class = curr.profile_model.class_name.lower()
            # Check for Item Types in AffixGroupEditor (Affixes Tab)
            if hasattr(curr, "config") and hasattr(curr.config, "item_type"):
                allowed_types = curr.config.item_type
            # Check for Item Types in UniqueWidget (Global Uniques Tab)
            if hasattr(curr, "unique_model") and hasattr(curr.unique_model, "item_type"):
                allowed_types = curr.unique_model.item_type
            curr = curr.parent()

        dialog = UniqueAspectDialog(self, self.unique_aspect, char_class, allowed_types)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.refresh_display()
            self.config_changed.emit()
        return result

    def refresh_display(self):
        name = Dataloader().aspect_unique_dict.get(self.unique_aspect.name, {}).get("name", self.unique_aspect.name)
        self.summary_label.setText(name.replace("_", " ").title())

        if self.unique_aspect.min_percent_of_aspect:
            self.threshold_label.setText(f"{self.unique_aspect.min_percent_of_aspect}%")
        elif self.unique_aspect.value is not None:
            self.threshold_label.setText(str(self.unique_aspect.value))
        else:
            self.threshold_label.setText("Any")

    def update_name(self, current_text=None):
        aspect_name = current_text or self.name_combo.currentText()
        aspect_name = aspect_name.strip()
        if aspect_name not in Dataloader().aspect_unique_dict:
            return
        self.unique_aspect.name = aspect_name
        self.update_parent_unique_aspects_title()

    def update_parent_unique_aspects_title(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, AffixGroupEditor):
                parent.refresh_unique_aspects_title()
                break
            parent = parent.parent()

    def refresh_value_input(self):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            self.value_edit.setPlaceholderText("Percent (0-100)")
            self.value_edit.setValidator(QIntValidator(0, 100, self.value_edit))
            display_value = (
                "" if self.unique_aspect.min_percent_of_aspect == 0 else str(self.unique_aspect.min_percent_of_aspect)
            )
        else:
            self.value_edit.setPlaceholderText("Value (optional)")
            self.value_edit.setValidator(QDoubleValidator(self.value_edit))
            display_value = "" if self.unique_aspect.value is None else str(self.unique_aspect.value)

        with QSignalBlocker(self.value_edit):
            self.value_edit.setText(display_value)

    def update_mode(self, current_text=None):
        mode = current_text or self.mode_combo.currentText()
        if mode == AFFIX_PERCENT_MODE:
            self.unique_aspect.value = None
        else:
            self.unique_aspect.min_percent_of_aspect = 0
        self.refresh_value_input()

    def update_value(self, value):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            try:
                percent = int(value) if value else 0
            except ValueError:
                return
            if not 0 <= percent <= 100:
                QMessageBox.warning(self, "Warning", "Min % must be between 0 and 100.")
                self.refresh_value_input()
                return
            self.unique_aspect.min_percent_of_aspect = percent
            self.unique_aspect.value = None
            return

        try:
            self.unique_aspect.value = float(value) if value else None
        except ValueError:
            return
        self.unique_aspect.min_percent_of_aspect = 0


class AffixSummaryWidget(QWidget):
    delete_requested = pyqtSignal()
    config_changed = pyqtSignal()

    def __init__(self, model: AffixFilterModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setObjectName("SummaryCard")
        self.setStyleSheet(_create_summary_card_style())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(22, 8, 10, 8)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; color: #e2e8f0;")
        self.main_layout.addWidget(self.summary_label, 1)

        self.threshold_label = QLabel()
        self.threshold_label.setMinimumWidth(60)
        self.threshold_label.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold;")
        self.main_layout.addWidget(self.threshold_label)

        self.delete_btn = _create_delete_btn()
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        self.main_layout.addWidget(self.delete_btn)

        self.refresh_display()

    @override
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        p.end()

    @override
    def mousePressEvent(self, event):
        if event is None or event.button() == Qt.MouseButton.LeftButton:
            self.open_config_dialog()

    def open_config_dialog(self) -> QDialog.DialogCode:
        # Gather context by crawling up the widget tree
        allowed_types = []
        is_global = False
        curr = self.parent()
        while curr:
            # Check for Item Types in AffixGroupEditor (Affixes Tab)
            if hasattr(curr, "config") and hasattr(curr.config, "item_type"):
                allowed_types = curr.config.item_type
                is_global = False
                break
            # If we hit UniqueWidget, we are in a Global Rule
            if hasattr(curr, "unique_model"):
                is_global = True
                break
            curr = curr.parent()

        dialog = AffixEditDialog(self, self.model, None if is_global else allowed_types)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.refresh_display()
            self.config_changed.emit()
        return result

    def refresh_display(self):
        name = Dataloader().affix_dict.get(self.model.name, self.model.name)
        if self.model.want_greater:
            name += " (GA)"

        if getattr(self.model, "required", False):
            self.summary_label.setText(f'<span style="color: #ef4444;">[REQ]</span> {name}')
        else:
            self.summary_label.setText(name)

        if self.model.min_percent_of_affix:
            self.threshold_label.setText(f"{self.model.min_percent_of_affix}%")
        elif self.model.value is not None:
            self.threshold_label.setText(str(self.model.value))
        else:
            self.threshold_label.setText("Any")


class AffixPoolWidget(QWidget):
    pool_delete_requested = pyqtSignal()
    config_changed = pyqtSignal()

    def __init__(self, pool: AffixFilterCountModel, parent=None):
        super().__init__(parent)
        self.pool = pool
        self.setObjectName("SummaryCard")
        self.setStyleSheet(_create_summary_card_style())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(22, 8, 10, 8)
        self.main_layout.setSpacing(10)

        # Container for labels on the left
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.affix_summary = QLabel()
        self.affix_summary.setWordWrap(True)
        self.affix_summary.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        text_layout.addWidget(self.affix_summary)

        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold;")
        text_layout.addWidget(self.count_label)

        self.main_layout.addLayout(text_layout, 1)

        # Hidden label used for internal state and dialog titles
        self.pool_name_label = QLabel()
        self.pool_name_label.setVisible(False)

        self.del_pool_btn = _create_delete_btn()
        self.del_pool_btn.setToolTip("Delete entire pool")
        self.del_pool_btn.clicked.connect(self.pool_delete_requested.emit)
        self.main_layout.addWidget(self.del_pool_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.refresh_display()

    @override
    def mousePressEvent(self, event):
        if event is None or event.button() == Qt.MouseButton.LeftButton:
            self.open_config_dialog()

    def open_config_dialog(self):
        # Find allowed types
        allowed_types = []
        is_global = False
        curr = self.parent()
        while curr:
            if hasattr(curr, "config") and hasattr(curr.config, "item_type"):
                allowed_types = curr.config.item_type
                is_global = False
                break
            if hasattr(curr, "unique_model"):
                is_global = True
                break
            curr = curr.parent()

        dialog = AffixPoolDialog(self, self.pool, self.pool_name_label.text(), None if is_global else allowed_types)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_display()
            self.config_changed.emit()

    def set_pool_name(self, name: str):
        self.pool_name_label.setText(name.upper())

    def refresh_display(self):
        max_val = "∞" if self.pool.max_count > 1000 else str(self.pool.max_count)
        self.count_label.setText(f"Min: {self.pool.min_count} / Max: {max_val}")
        self.affix_summary.setText(_affix_summary(self.pool))


class AffixWidget(QWidget):
    delete_requested = pyqtSignal()

    def __init__(self, affix: AffixFilterModel, parent=None, allowed_item_types: list[ItemType] | None = None):
        super().__init__(parent)
        self.affix = affix
        self.allowed_item_types = allowed_item_types
        self.setStyleSheet("background: transparent; border: none;")
        self.setup_ui()

    def setup_ui(self):
        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 5, 0, 5)
        main_vbox.setSpacing(8)

        self.create_affix_name_combobox()
        self.create_greater_checkbox()
        self.create_required_checkbox()
        self.create_mode_combobox()
        self.create_value_input()

        self.mode_combo.currentTextChanged.connect(self.update_mode)
        self.update_mode(self.mode_combo.currentText())

        # Top row: Affix selection
        main_vbox.addWidget(self.name_combo)

        # Bottom row: Options and Values
        bottom_hbox = QHBoxLayout()
        bottom_hbox.setSpacing(10)
        bottom_hbox.addWidget(self.required_checkbox)
        bottom_hbox.addWidget(self.greater_checkbox)
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(self.mode_combo)
        bottom_hbox.addWidget(self.value_edit)
        main_vbox.addLayout(bottom_hbox)

    def create_affix_name_combobox(self):
        affix_dict = Dataloader().affix_dict
        filtered_affixes = sorted(affix_dict.values())

        self.name_combo = TruncatingComboBox(parent=self)
        self.name_combo.setEditable(True)
        self.name_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.name_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.name_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.name_combo.addItems(filtered_affixes)
        self.name_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if self.affix.name in affix_dict:
            self.name_combo.setCurrentText(affix_dict[self.affix.name])
        self.name_combo.currentTextChanged.connect(self.update_name)

    def create_required_checkbox(self):
        self.required_checkbox = CheckmarkCheckBox("Required")
        self.required_checkbox.setChecked(getattr(self.affix, "required", False))
        self.required_checkbox.setFixedWidth(85)
        self.required_checkbox.stateChanged.connect(self.update_required)

    def update_required(self):
        self.affix.required = self.required_checkbox.isChecked()

    def create_greater_checkbox(self):
        self.greater_checkbox = CheckmarkCheckBox("GA")
        self.greater_checkbox.setChecked(getattr(self.affix, "want_greater", False))
        self.greater_checkbox.setFixedWidth(80)
        self.greater_checkbox.setProperty("greaterCheckbox", True)  # noqa: FBT003
        self._refresh_widget_style(self.greater_checkbox)
        self.greater_checkbox.stateChanged.connect(self.update_greater)
        self.greater_checkbox.stateChanged.connect(self.update_parent_count_label)

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def update_parent_count_label(self):
        parent = self.parent()
        while parent:
            if isinstance(parent, AffixGroupEditor):
                parent.update_greater_count_label()
                parent.sync_min_greater_from_checkboxes()
                break
            parent = parent.parent()

    def create_mode_combobox(self):
        self.mode_combo = IgnoreScrollWheelComboBox()
        self.mode_combo.setFixedWidth(80)
        self.mode_combo.addItems([AFFIX_VALUE_MODE, AFFIX_PERCENT_MODE])
        if self.affix.min_percent_of_affix:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        else:
            self.mode_combo.setCurrentText(AFFIX_VALUE_MODE)

    def create_value_input(self):
        self.value_edit = QLineEdit()
        self.value_edit.setFixedWidth(80)
        self.value_edit.textChanged.connect(self.update_value)

    def update_name(self, current_text=None):
        """Update the model only when the editable combobox contains a valid affix."""
        reverse_dict = {v: k for k, v in Dataloader().affix_dict.items()}
        affix_name = reverse_dict.get(current_text or self.name_combo.currentText())
        if affix_name is None:
            return
        self.affix.name = affix_name

    def refresh_value_input(self):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            self.value_edit.setPlaceholderText("Percent (0-100)")
            self.value_edit.setValidator(QIntValidator(0, 100, self.value_edit))
            display_value = "" if self.affix.min_percent_of_affix == 0 else str(self.affix.min_percent_of_affix)
        else:
            self.value_edit.setPlaceholderText("Value (optional)")
            self.value_edit.setValidator(QDoubleValidator(self.value_edit))
            display_value = "" if self.affix.value is None else str(self.affix.value)

        with QSignalBlocker(self.value_edit):
            self.value_edit.setText(display_value)

    def update_mode(self, current_text=None):
        mode = current_text or self.mode_combo.currentText()
        if mode == AFFIX_PERCENT_MODE:
            self.affix.value = None
        else:
            self.affix.min_percent_of_affix = 0
        self.refresh_value_input()

    def update_value(self, value):
        if self.mode_combo.currentText() == AFFIX_PERCENT_MODE:
            try:
                percent = int(value) if value else 0
            except ValueError:
                return
            if not 0 <= percent <= 100:
                QMessageBox.warning(self, "Warning", "Min % must be between 0 and 100.")
                self.refresh_value_input()
                return
            self.affix.min_percent_of_affix = percent
            self.affix.value = None
            return

        try:
            self.affix.value = float(value) if value else None
        except ValueError:
            return
        self.affix.min_percent_of_affix = 0

    def update_greater(self):
        self.affix.want_greater = self.greater_checkbox.isChecked()

    def set_min_percent(self, percent: int, convert_mode: bool = False):
        if convert_mode and self.mode_combo.currentText() != AFFIX_PERCENT_MODE:
            self.mode_combo.setCurrentText(AFFIX_PERCENT_MODE)
        if self.mode_combo.currentText() != AFFIX_PERCENT_MODE:
            return
        self.value_edit.setText(str(percent))


class AffixesTab(QWidget):
    def __init__(self, affixes_model: list[DynamicItemFilterModel], parent=None):
        super().__init__(parent)
        self.affixes_model = affixes_model
        self._current_slot_name = ""
        self._current_slot_item_types = []
        self.loaded = False
        self.settings = QSettings("d4lf", "profile_editor")
        self.item_names = []
        self.item_data_map: dict[str, DynamicItemFilterModel] = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load(self):
        with contextlib.suppress(RuntimeError):
            if not self.loaded:
                self.setup_ui()
                self.loaded = True

    def setup_ui(self):
        """Populate the grid layout with existing groups."""
        self.setStyleSheet("background: transparent; border: none;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setStyleSheet("""
            QTabWidget { background: transparent; border: none; }
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #1a1a1a;
                color: #94a3b8;
                padding: 8px 30px 8px 12px;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::close-button:hover { background-color: rgba(255, 255, 255, 0.1); }
            QTabBar::tab:selected {
                background: #1e3a5f;
                color: #e2e8f0;
                border: 1px solid #3b82f6;
                border-bottom: 2px solid #3b82f6;
            }
            QTabBar::tab:last, QTabBar::tab:selected:last, QTabBar::tab:only-one, QTabBar::tab:selected:only-one {
                background: #06201b;
                color: #22c55e;
                border: 1px solid #064e3b;
                border-bottom: 1px solid #064e3b;
            }
        """)
        with QSignalBlocker(self.tab_widget):
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.tabCloseRequested.connect(self.close_tab)
            self.tab_widget.currentChanged.connect(self._on_tab_changed)
            self.tab_widget.tabBar().tabBarClicked.connect(self._on_tab_bar_clicked)

            # Add a persistent "+" tab at the end
            self.tab_widget.addTab(QWidget(), "+")

            self.item_names = []
            self.item_data_map.clear()
            for affix_group in self.affixes_model:
                for item_name in affix_group.root:
                    if item_name in self.item_names:
                        QMessageBox.warning(
                            self, "Warning", f"Item name already exist please rename {item_name} in the profile file."
                        )
                        continue
                    self.item_names.append(item_name)
                    self.item_data_map[item_name] = affix_group
                    # Insert before the "+" tab
                    self.tab_widget.insertTab(self.tab_widget.count() - 1, QWidget(), item_name)

        self._update_plus_tab_button()
        self.main_layout.addWidget(self.tab_widget)

    def show_message(self, text):
        QMessageBox.information(self, "Info", text)

    def _on_tab_changed(self, index):
        if index >= 0 and self.tab_widget.tabText(index) == "+":
            self.add_item_type()

    def _on_tab_bar_clicked(self, index):
        # This handles clicking the "+" tab when it's already selected
        if index >= 0 and self.tab_widget.tabText(index) == "+" and self.tab_widget.currentIndex() == index:
            self.add_item_type()

    def _update_plus_tab_button(self):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                self.tab_widget.tabBar().setTabButton(i, QTabBar.ButtonPosition.RightSide, None)
                self.tab_widget.setTabToolTip(i, "Create Item")

    def _ensure_tab_instantiated(self, index: int):
        if index < 0 or index >= self.tab_widget.count():
            return
        if not isinstance(self.tab_widget.widget(index), AffixGroupEditor):
            item_name = self.item_names[index]
            affix_group = self.item_data_map[item_name]
            is_current = self.tab_widget.currentIndex() == index
            with QSignalBlocker(self.tab_widget):
                editor = AffixGroupEditor(affix_group)
                editor.duplicate_requested.connect(self.duplicate_item_tab)
                self.tab_widget.removeTab(index)
                self.tab_widget.insertTab(index, editor, item_name)
                if is_current:
                    self.tab_widget.setCurrentIndex(index)

    def add_item_type(self):
        plus_idx = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                plus_idx = i
                break

        # Switch to previous tab if we were triggered by clicking the "+" tab
        if self.tab_widget.currentIndex() == plus_idx and plus_idx > 0:
            self.tab_widget.setCurrentIndex(plus_idx - 1)

        if self._current_slot_name:
            base_name = self._current_slot_name.replace(" ", "")
            new_name = base_name
            if new_name in self.item_names:
                i = 2
                while f"{base_name}{i}" in self.item_names:
                    i += 1
                new_name = f"{base_name}{i}"

            item_model = ItemFilterModel(item_type=self._current_slot_item_types or [])
            dynamic_filter = DynamicItemFilterModel({new_name: item_model})

            self.item_names.append(new_name)
            self.item_data_map[new_name] = dynamic_filter
            group = AffixGroupEditor(dynamic_filter)
            self.tab_widget.insertTab(plus_idx, group, new_name)
            self.affixes_model.append(dynamic_filter)
            self.tab_widget.setCurrentIndex(plus_idx)
            self._update_plus_tab_button()
            return

        # Fallback for manual creation outside of doll context
        dialog = CreateItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = dialog.get_value()
            for item_name in item.root:
                group = AffixGroupEditor(item)
                self.item_names.append(item_name)
                self.item_data_map[item_name] = item
                self.tab_widget.insertTab(plus_idx, group, item_name)
                self.affixes_model.append(item)
                self.tab_widget.setCurrentIndex(plus_idx)
                self._update_plus_tab_button()

    def close_tab(self, index):
        if self.tab_widget.tabText(index) == "+":
            return

        item_name = self.item_names[index]
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the item filter '{item_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        with QSignalBlocker(self.tab_widget):
            name = self.item_names.pop(index)
            self.item_data_map.pop(name, None)
            self.tab_widget.removeTab(index)
            self.affixes_model.pop(index)
        self._update_plus_tab_button()

    def duplicate_item_tab(self, original_filter: DynamicItemFilterModel):
        # Find a unique name for the duplicated item
        original_name = next(iter(original_filter.root.keys()))
        new_name_base = f"{original_name} (Copy)"
        new_name = new_name_base
        i = 1
        while new_name in self.item_names:
            i += 1
            new_name = f"{new_name_base} {i}"

        # Create a deep copy of the filter model
        new_filter_model = copy.deepcopy(original_filter)
        # Update the key in the root dictionary to the new name
        new_filter_model.root = {new_name: new_filter_model.root.pop(original_name)}

        # Add to our internal lists and create a new tab
        self.item_names.append(new_name)
        self.item_data_map[new_name] = new_filter_model
        self.affixes_model.append(new_filter_model)

        # Find the "+" tab index to insert before it
        plus_idx = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                plus_idx = i
                break

        # Create the actual editor widget and insert the tab
        editor = AffixGroupEditor(new_filter_model)
        editor.duplicate_requested.connect(self.duplicate_item_tab)

        if plus_idx != -1:
            self.tab_widget.insertTab(plus_idx, editor, new_name)
            self.tab_widget.setCurrentIndex(plus_idx)
        self._update_plus_tab_button()

    def remove_item_type(self):
        dialog = DeleteItem(self.item_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item_names_to_delete = dialog.get_value()
            for item_name in item_names_to_delete:
                index = self.item_names.index(item_name)
                self.item_names.remove(item_name)
                self.item_data_map.pop(item_name, None)
                self.tab_widget.removeTab(index)
                self.affixes_model.pop(index)
            self._update_plus_tab_button()
            return

    def set_all_min_greater_affix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_greater_affix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    continue

                tab = self.tab_widget.widget(i)
                item_name = self.item_names[i]

                if isinstance(tab, AffixGroupEditor):
                    if tab.auto_sync_checkbox.isChecked():
                        continue
                    tab.min_greater.setValue(min_greater_affix)
                    tab.update_min_greater_affix()
                else:
                    # Placeholder: check settings for auto-sync status
                    if self.settings.value(f"auto_sync_ga_{item_name}", defaultValue=False, type=bool):
                        continue
                    self.item_data_map[item_name].root[item_name].min_greater_affix_count = min_greater_affix

    def convert_all_to_min_percent_of_affix(self):
        dialog = MinPercentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            percent = dialog.get_value()
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    continue

                tab = self.tab_widget.widget(i)
                item_name = self.item_names[i]

                if isinstance(tab, AffixGroupEditor):
                    tab.convert_all_to_min_percent_of_affix(percent)
                else:
                    # Placeholder: update the data model directly
                    config = self.item_data_map[item_name].root[item_name]
                    for pool in config.affix_pool:
                        for affix in pool.count:
                            affix.min_percent_of_affix = percent
                            affix.value = None

    def set_all_min_power(self):
        dialog = MinPowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_power = dialog.get_value()
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    continue

                tab = self.tab_widget.widget(i)
                item_name = self.item_names[i]

                if isinstance(tab, AffixGroupEditor):
                    tab.min_power.setValue(min_power)
                    tab.update_min_power()
                else:
                    # Placeholder: Update the model directly
                    self.item_data_map[item_name].root[item_name].min_power = min_power

    def filter_by_item_types(self, item_types: list[ItemType] | None, slot_name: str | None = None):
        """Show only tabs that match the provided item types."""
        if not hasattr(self, "tab_widget"):
            return
        self._current_slot_name = slot_name
        self._current_slot_item_types = item_types

        # Normalize slot name for comparison (e.g., "Dual-Wield 1" -> "dualwield1")
        slot_match_name = slot_name.lower().replace(" ", "").replace("-", "") if slot_name else None
        is_rings = slot_match_name == "rings"
        is_dw_all = slot_match_name == "dualwields"
        is_ring_2 = slot_match_name == "ring2"
        is_ring_1 = slot_match_name == "ring1"
        is_dw_1 = slot_match_name == "dualwield1"
        is_dw_2 = slot_match_name == "dualwield2"
        is_dw_ranged = slot_match_name == "rangedweapon"
        is_bludgeoning = slot_match_name == "bludgeoning"
        is_slashing = slot_match_name == "slashing"
        is_main_hand = slot_match_name == "mainhand"
        type_names = [t.value.lower().replace(" ", "").replace("-", "") for t in item_types] if item_types else []

        # Determine if we have any tabs that specifically match this slot's name.
        # This allows us to separate slots like "Ring 1" and "Ring 2" if the user has rules for both.
        has_exact_match = False
        if slot_match_name:
            for i in range(self.tab_widget.count()):
                tab_text = self.tab_widget.tabText(i).lower().replace(" ", "").replace("-", "")
                if (
                    tab_text == slot_match_name
                    or (slot_match_name and slot_match_name in tab_text)
                    or (tab_text and tab_text in slot_match_name)
                    or (is_rings and "ring" in tab_text)
                    or (is_dw_all and "dualwield" in tab_text)
                    or (is_ring_1 and tab_text == "ring")
                    or (is_dw_1 and tab_text == "dualwield")
                    or (is_dw_2 and tab_text == "dualwield")
                    or (is_dw_ranged and tab_text == "ranged")
                    or (
                        tab_text in type_names
                        and not (is_ring_2 or is_dw_2 or is_dw_1 or is_bludgeoning or is_slashing or is_dw_ranged)
                    )
                    or (is_main_hand and tab_text == "weapon")
                ):
                    has_exact_match = True
                    break

        with QSignalBlocker(self.tab_widget):
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    self.tab_widget.setTabVisible(i, True)  # noqa: FBT003
                    continue

                item_name = self.item_names[i]
                affix_group = self.item_data_map[item_name]
                config = affix_group.root[item_name]
                tab_text = self.tab_widget.tabText(i).lower().replace(" ", "").replace("-", "")

                type_match = not item_types or not config.item_type or any(t in config.item_type for t in item_types)

                if has_exact_match:
                    visible = type_match and (
                        tab_text == slot_match_name
                        or (slot_match_name and slot_match_name in tab_text)
                        or (tab_text and tab_text in slot_match_name)
                        or (is_rings and "ring" in tab_text)
                        or (is_dw_all and "dualwield" in tab_text)
                        or (is_ring_1 and tab_text == "ring")
                        or (is_dw_1 and tab_text == "dualwield")
                        or (is_dw_2 and tab_text == "dualwield")
                        or (is_dw_ranged and tab_text == "ranged")
                        or (
                            tab_text in type_names
                            and not (is_ring_2 or is_dw_2 or is_dw_1 or is_bludgeoning or is_slashing or is_dw_ranged)
                        )
                        or (is_main_hand and tab_text == "weapon")
                    )
                else:
                    visible = type_match

                if visible and not isinstance(self.tab_widget.widget(i), AffixGroupEditor):
                    self._ensure_tab_instantiated(i)
                self.tab_widget.setTabVisible(i, visible)

            # Ensure a valid content tab is focused instead of the '+' tab
            curr = self.tab_widget.currentIndex()
            if curr == -1 or not self.tab_widget.isTabVisible(curr) or self.tab_widget.tabText(curr) == "+":
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.isTabVisible(i) and self.tab_widget.tabText(i) != "+":
                        self.tab_widget.setCurrentIndex(i)
                        break
