from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QStyle, QVBoxLayout, QWidget

from src.profiles import AffixFilterCountModel, AffixFilterModel
from src.profiles.affix.helpers import affix_dict_for_widget
from src.profiles.affix.widget import AffixWidget
from src.profiles.editor.dialogs import IgnoreScrollWheelSpinBox

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class AffixPoolWidget(QWidget):
    def __init__(self, pool: AffixFilterCountModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pool = pool
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        config_layout = QHBoxLayout()
        config_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        min_count_label = QLabel("Min Count:")
        min_count_label.setMaximumWidth(100)
        min_count_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(min_count_label)
        config_layout.addWidget(min_count_label)

        self.min_count = IgnoreScrollWheelSpinBox()
        self.min_count.setValue(self.pool.min_count)
        self.min_count.setMaximumWidth(100)
        self.min_count.valueChanged.connect(self.update_min_count)
        config_layout.addWidget(self.min_count)
        config_layout.addSpacing(150)

        max_count_label = QLabel("Max Count:")
        max_count_label.setMaximumWidth(100)
        max_count_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(max_count_label)
        config_layout.addWidget(max_count_label)

        self.max_count = IgnoreScrollWheelSpinBox()
        self.max_count.setValue(min(self.pool.max_count, 2147483647))
        self.max_count.setMaximumWidth(100)
        self.max_count.valueChanged.connect(self.update_max_count)
        config_layout.addWidget(self.max_count)

        layout.addLayout(config_layout)

        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        affix_label = QLabel("Affixes")
        affix_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(affix_label)

        greater_label = QLabel("Greater")
        greater_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(greater_label)

        mode_label = QLabel("Mode")
        mode_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(mode_label)

        value_label = QLabel("Threshold")
        value_label.setProperty("affixHeaderLabel", True)  # ruff:ignore[boolean-positional-value-in-call]
        self._refresh_widget_style(value_label)

        title_layout.addSpacing(250)
        title_layout.addWidget(affix_label)
        title_layout.addSpacing(400)
        title_layout.addWidget(greater_label)
        title_layout.addSpacing(70)
        title_layout.addWidget(mode_label)
        title_layout.addSpacing(85)
        title_layout.addWidget(value_label)

        self.affix_list = QListWidget()
        self.affix_list.setMinimumHeight(200)
        self.affix_list.setAlternatingRowColors(True)
        for affix in self.pool.count:
            self.add_affix_item(affix)

        affix_btn_layout = QHBoxLayout()
        add_affix_btn = QPushButton("Add Affix")
        add_affix_btn.clicked.connect(self.add_affix)
        affix_btn_layout.addWidget(add_affix_btn)

        remove_affix_btn = QPushButton("Remove Affix")
        remove_affix_btn.clicked.connect(lambda: self.remove_selected(self.affix_list))
        affix_btn_layout.addWidget(remove_affix_btn)

        layout.addLayout(affix_btn_layout)
        layout.addLayout(title_layout)
        layout.addWidget(self.affix_list)

        self.setLayout(layout)

    def _refresh_widget_style(self, widget: QWidget) -> None:
        style = cast("QStyle", widget.style())
        style.unpolish(widget)
        style.polish(widget)

    def add_affix_item(self, affix: AffixFilterModel) -> None:
        item = QListWidgetItem()
        widget = AffixWidget(affix, self)
        item.setSizeHint(widget.sizeHint())
        self.affix_list.addItem(item)
        self.affix_list.setItemWidget(item, widget)

    def get_affix_dict(self) -> dict[str, str]:
        return affix_dict_for_widget(self)

    def add_affix(self) -> None:
        affix_dict = self.get_affix_dict()
        new_affix = AffixFilterModel(name=next(iter(affix_dict.keys()), ""), value=None)
        self.pool.count.append(new_affix)
        self.add_affix_item(new_affix)

    def remove_selected(self, list_widget: QListWidget) -> None:
        for item in list_widget.selectedItems():
            row = list_widget.row(item)
            list_widget.takeItem(row)
            del self.pool.count[row]

    def update_min_count(self) -> None:
        self.pool.min_count = self.min_count.value()

    def update_max_count(self) -> None:
        self.pool.max_count = self.max_count.value()
