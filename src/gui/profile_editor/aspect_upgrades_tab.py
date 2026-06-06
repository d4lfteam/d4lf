from typing import override

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)

from src.gui.models.dialog import AddAspectUpgrade
from src.gui.profile_editor.affixes_tab import (
    QPainter,
    _create_column_header,
    _create_delete_btn,
    _create_summary_card_style,
)

ASPECT_UPGRADES_TABNAME = "Aspect Upgrades"


class AspectUpgradeSummaryWidget(QWidget):
    delete_requested = pyqtSignal()

    def __init__(self, aspect_key: str, parent=None):
        super().__init__(parent)
        self.aspect_key = aspect_key
        self.setObjectName("SummaryCard")
        self.setStyleSheet(_create_summary_card_style())
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)

        # Format the aspect key into a friendly title
        display_name = self.aspect_key.replace("_", " ").title()
        self.summary_label = QLabel(display_name)
        self.summary_label.setStyleSheet("font-weight: bold; color: #e2e8f0;")
        self.main_layout.addWidget(self.summary_label, 1)

        self.delete_btn = _create_delete_btn()
        self.delete_btn.clicked.connect(self.delete_requested.emit)
        self.main_layout.addWidget(self.delete_btn)

    @override
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        p.end()


class AspectUpgradesTab(QWidget):
    def __init__(self, aspect_upgrades: list[str], parent=None):
        super().__init__(parent)
        self.aspect_upgrades = aspect_upgrades
        self.loaded = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header = _create_column_header("Aspect Upgrades", self.add_aspect)
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

        # Populate initial items
        for aspect in self.aspect_upgrades:
            self.add_aspect_item(aspect)

        self.setLayout(main_layout)

    def add_aspect_item(self, aspect_key: str):
        widget = AspectUpgradeSummaryWidget(aspect_key)
        widget.delete_requested.connect(lambda: self.remove_aspect_item(widget))
        self.list_layout.addWidget(widget)

    def add_aspect(self):
        dialog = AddAspectUpgrade(self.aspect_upgrades)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            aspect_upgrade = dialog.get_value()
            if aspect_upgrade:
                self.aspect_upgrades.append(aspect_upgrade)
                self.add_aspect_item(aspect_upgrade)

    def remove_aspect_item(self, widget: AspectUpgradeSummaryWidget):
        aspect_key = widget.aspect_key
        if aspect_key in self.aspect_upgrades:
            self.aspect_upgrades.remove(aspect_key)
        widget.setParent(None)
        widget.deleteLater()
