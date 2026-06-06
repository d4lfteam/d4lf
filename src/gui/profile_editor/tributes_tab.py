import contextlib
from typing import override

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import ItemRarity, TributeFilterModel
from src.dataloader import Dataloader
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox
from src.gui.profile_editor.affixes_tab import (
    QPainter,
    TruncatingComboBox,
    _create_column_header,
    _create_delete_btn,
    _create_summary_card_style,
)

TRIBUTES_TABNAME = "Tributes"


class TributeSummaryWidget(QWidget):
    delete_requested = pyqtSignal()
    config_changed = pyqtSignal()

    def __init__(self, model: TributeFilterModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setObjectName("SummaryCard")
        self.setStyleSheet(_create_summary_card_style())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold; color: #e2e8f0;")
        text_layout.addWidget(self.name_label)

        self.details_label = QLabel()
        self.details_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.details_label.setWordWrap(True)
        text_layout.addWidget(self.details_label)

        self.main_layout.addLayout(text_layout, 1)

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
        dialog = TributeEditDialog(self, self.model)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.refresh_display()
            self.config_changed.emit()
        return result

    def refresh_display(self):
        if self.model.name:
            name = Dataloader().tribute_dict.get(self.model.name, self.model.name)
            self.name_label.setText(name.replace("Tribute of ", ""))
        else:
            self.name_label.setText("Broad Rarity Filter")

        rarity_text = "All Rarities"
        if self.model.rarities:
            rarity_text = ", ".join(r.name.title() for r in self.model.rarities)
        self.details_label.setText(rarity_text)


class TributeEditDialog(QDialog):
    def __init__(self, parent: QWidget, model: TributeFilterModel):
        super().__init__(parent)
        self.setWindowTitle("Configure Tribute Rule")
        self.setMinimumWidth(500)
        self.model = model
        self.rarity_checkboxes: dict[ItemRarity, CheckmarkCheckBox] = {}
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
            QGroupBox {
                font-weight: bold;
                color: #3b82f6;
                border: 1px solid #334155;
                margin-top: 1.1em;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
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
        header = QLabel("Tribute Rule Configuration")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 5px;")
        layout.addWidget(header)

        desc = QLabel("Set a specific tribute or configure rarity-based filtering.")
        desc.setStyleSheet("font-size: 12px; color: #94a3b8; font-style: italic; margin-bottom: 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()

        self.name_combo = TruncatingComboBox()
        self.name_combo.addItems(["[None / Rarity Only]"] + sorted(Dataloader().tribute_dict.values()))
        if self.model.name:
            self.name_combo.setCurrentText(Dataloader().tribute_dict.get(self.model.name, self.model.name))
        else:
            self.name_combo.setCurrentIndex(0)
        form.addRow("Tribute:", self.name_combo)
        layout.addLayout(form)

        rarity_group = QGroupBox("Target Rarities")
        rarity_layout = QVBoxLayout(rarity_group)
        for rarity in ItemRarity:
            cb = CheckmarkCheckBox(rarity.name.title())
            cb.setChecked(rarity in self.model.rarities)
            self.rarity_checkboxes[rarity] = cb
            rarity_layout.addWidget(cb)
        layout.addWidget(rarity_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save_and_accept(self):
        val = self.name_combo.currentText()
        if val == "[None / Rarity Only]":
            self.model.name = None
        else:
            reverse_dict = {v: k for k, v in Dataloader().tribute_dict.items()}
            self.model.name = reverse_dict.get(val)

        self.model.rarities = [r for r, cb in self.rarity_checkboxes.items() if cb.isChecked()]
        self.accept()


class TributesTab(QWidget):
    def __init__(self, tributes: list[TributeFilterModel] | None, parent=None):
        super().__init__(parent)
        self.tributes = tributes if tributes is not None else []
        self.loaded = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load(self):
        with contextlib.suppress(RuntimeError):
            if not self.loaded:
                self.setup_ui()
                self.loaded = True

    def setup_ui(self):
        self.setStyleSheet("background: transparent; border: none;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.header = QLabel("Tributes")
        self.header.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 10px; background: transparent; border: none;"
        )
        main_layout.addWidget(self.header)

        self.desc = QLabel(
            "Add tributes or rarity-based rules you want to keep. These rules are evaluated independently."
        )
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet(
            "font-size: 13px; color: #94a3b8; font-style: italic; margin-bottom: 15px; background: transparent; border: none;"
        )
        main_layout.addWidget(self.desc)

        header = _create_column_header("Tributes", self.add_tribute)
        main_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.Panel)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #2d2d2d; border-left: none; background-color: #121212; }")

        self.scroll_widget = QWidget()
        self.list_layout = QVBoxLayout(self.scroll_widget)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setContentsMargins(10, 10, 10, 10)
        self.list_layout.setSpacing(4)

        scroll.setWidget(self.scroll_widget)
        main_layout.addWidget(scroll)

        self.init_tributes()
        self.setLayout(main_layout)

    def init_tributes(self):
        for tribute in self.tributes:
            self.add_tribute_widget(tribute)

    def add_tribute_widget(self, model: TributeFilterModel):
        widget = TributeSummaryWidget(model)
        widget.delete_requested.connect(lambda: self.remove_tribute_item(widget))
        self.list_layout.addWidget(widget)
        return widget

    def add_tribute(self):
        tribute_id = next(iter(Dataloader().tribute_dict.keys()))
        new_rule = TributeFilterModel(name=tribute_id, rarities=[])
        self.tributes.append(new_rule)
        widget = self.add_tribute_widget(new_rule)
        if widget.open_config_dialog() == QDialog.DialogCode.Rejected:
            self.remove_tribute_item(widget)

    def remove_tribute_item(self, widget: TributeSummaryWidget):
        if widget.model in self.tributes:
            self.tributes.remove(widget.model)
        widget.setParent(None)
        widget.deleteLater()
