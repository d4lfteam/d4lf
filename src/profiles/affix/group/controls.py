from typing import Any, cast

from PyQt6.QtWidgets import QDialog, QWidget

from src.profiles.affix.helpers import _item_type_summary
from src.profiles.affix.picker import ItemTypePicker
from src.profiles.affix.pool import AffixPoolWidget
from src.profiles.affix.widget import AffixWidget
from src.profiles.editor import Container, RarityPicker, rarity_summary, refresh_widget_style

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class _AffixGroupControlsMixin:
    def refresh_item_type_summary(self: Any):
        self.item_type_line_edit.setText(_item_type_summary(self.config.item_type))

    def edit_item_types(self: Any):
        item_type_picker = ItemTypePicker(cast("QWidget", self), self.item_types, self.config.item_type)
        if item_type_picker.exec() == QDialog.DialogCode.Accepted:
            self.config.item_type = item_type_picker.get_selected_item_types()
            self.refresh_item_type_summary()

    def refresh_rarity_summary(self: Any):
        self.rarity_line_edit.setText(rarity_summary(self.config.rarities))

    def edit_rarities(self: Any):
        rarity_picker = RarityPicker(cast("QWidget", self), self.config.rarities)
        if rarity_picker.exec() == QDialog.DialogCode.Accepted:
            self.config.rarities = rarity_picker.get_selected_rarities()
            self.refresh_rarity_summary()

    def update_min_power(self: Any):
        self.config.min_power = self.min_power.value()

    def update_min_greater_affix(self: Any):
        self.config.min_greater_affix_count = self.min_greater.value()

    def toggle_auto_sync(self: Any):
        is_auto_sync = self.auto_sync_checkbox.isChecked()

        # Save UI-only state (replaces writing to config)
        self.settings.setValue(f"auto_sync_ga_{self.item_name}", is_auto_sync)

        # Keep your existing behavior
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            self.min_greater.setProperty("autoSyncSpin", True)  # ruff:ignore[boolean-positional-value-in-call]
            refresh_widget_style(self.min_greater)

            self.affix_pool_container.expand()
            self.inherent_pool_container.expand()

            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setProperty("autoSyncSpin", False)  # ruff:ignore[boolean-positional-value-in-call]
            refresh_widget_style(self.min_greater)

    def _update_auto_sync_count(self: Any):
        count = self.count_want_greater_affixes()
        self.min_greater.setValue(count)
        self.update_greater_count_label()

    def sync_min_greater_from_checkboxes(self: Any):
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)

    def _ensure_pool_widgets_initialized(self: Any):
        for container in (self.affix_pool_container, self.inherent_pool_container):
            was_visible = container.content_widget.isVisible()
            if container.header.first_expansion:
                container.expand()
                if not was_visible:
                    container.collapse()

    def iter_affix_widgets(self: Any):
        self._ensure_pool_widgets_initialized()

        # Inherents do not participate in Greater Affix auto-sync or bulk Min % updates.
        for i in range(self.affix_pool_layout.count()):
            item = self.affix_pool_layout.itemAt(i)
            if item is None:
                continue
            container = item.widget()
            if not isinstance(container, Container):
                continue
            pool_layout = container.content_widget.layout()
            if pool_layout is None:
                continue
            pool_item = pool_layout.itemAt(0)
            if pool_item is None:
                continue
            pool_widget = pool_item.widget()
            if not isinstance(pool_widget, AffixPoolWidget):
                continue
            for j in range(pool_widget.affix_list.count()):
                list_item = pool_widget.affix_list.item(j)
                affix_widget = pool_widget.affix_list.itemWidget(list_item)
                if isinstance(affix_widget, AffixWidget):
                    yield affix_widget

    def count_want_greater_affixes(self: Any):
        return sum(affix.want_greater for pool in self.config.affix_pool for affix in pool.count)

    def update_greater_count_label(self: Any):
        count = self.count_want_greater_affixes()
        if count == 0:
            self.greater_count_label.setText("(no greater affixes marked)")
        elif count == 1:
            self.greater_count_label.setText("(1 greater affix marked)")
        else:
            self.greater_count_label.setText(f"({count} greater affixes marked)")

    def convert_all_to_min_percent_of_affix(self: Any, percent: int):
        for affix_widget in self.iter_affix_widgets():
            affix_widget.set_min_percent(percent, convert_mode=True)
