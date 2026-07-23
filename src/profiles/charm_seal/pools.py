from typing import Any, cast

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget

from src.item import Dataloader
from src.profiles import AffixFilterCountModel, AffixFilterModel
from src.profiles.affix import AffixPoolWidget, AffixWidget, DeleteAffixPool
from src.profiles.editor import Container, RarityPicker, rarity_summary, refresh_widget_style

CHARMS_TABNAME = "Charms"
SEALS_TABNAME = "Seals"


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


class _CharmSealPoolsMixin:
    def add_affix_pool(self: Any):
        affix_dict = Dataloader().charm_affix_dict if self.is_charm else Dataloader().seal_affix_dict
        default_affix_name = next(iter(affix_dict.keys()), "")
        default_affix = AffixFilterModel(name=default_affix_name, value=None)
        new_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        self.config.affix_pool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def remove_selected(self: Any, layout_widget: QVBoxLayout):
        nb_pool = layout_widget.count()
        dialog = DeleteAffixPool(nb_pool)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            to_delete = dialog.get_value()
            to_delete_list = []
            for i in range(layout_widget.count()):
                item = layout_widget.itemAt(i)
                if item is None:
                    continue
                widget = item.widget()
                if isinstance(widget, Container) and widget.header.name in to_delete:
                    to_delete_list.append((widget, i))
            to_delete_list.reverse()
            for widget, index in to_delete_list:
                widget.setParent(None)
                self.config.affix_pool.pop(index)
            self.update_affix_pool_names(layout_widget)
            QTimer.singleShot(50, self.update_greater_count_label)

    def update_affix_pool_names(self: Any, layout_widget: QVBoxLayout):
        for i in range(layout_widget.count()):
            item = layout_widget.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if isinstance(widget, Container):
                widget.header.set_name(f"Count {i}")

    # --- Rarities ---

    def edit_rarities(self: Any):
        dialog = RarityPicker(cast("QWidget", self), self.config.rarities)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.rarities = dialog.get_selected_rarities()
            self.refresh_rarity_summary()

    def refresh_rarity_summary(self: Any):
        self.rarity_line_edit.setText(rarity_summary(self.config.rarities))

    # --- Auto Sync minGreaterAffixCount ---

    def update_min_greater_affix(self: Any):
        self.config.min_greater_affix_count = self.min_greater.value()

    def toggle_auto_sync(self: Any, state):
        is_auto_sync = state == Qt.CheckState.Checked.value
        self.settings.setValue(f"auto_sync_ga_{self.type_prefix}_{self.item_name}", is_auto_sync)
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            self.min_greater.setProperty("autoSyncSpin", True)  # ruff:ignore[boolean-positional-value-in-call]
            refresh_widget_style(self.min_greater)
            self.affix_pool_container.expand()
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setProperty("autoSyncSpin", False)  # ruff:ignore[boolean-positional-value-in-call]
            refresh_widget_style(self.min_greater)

    def sync_min_greater_from_checkboxes(self: Any):
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)

    def _ensure_pool_widgets_initialized(self: Any):
        was_visible = self.affix_pool_container.content_widget.isVisible()
        if self.affix_pool_container.header.first_expansion:
            self.affix_pool_container.expand()
            if not was_visible:
                self.affix_pool_container.collapse()

    def iter_affix_widgets(self: Any):
        self._ensure_pool_widgets_initialized()
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

    def count_want_greater_affixes(self: Any) -> int:
        want_greater_count = 0
        if not hasattr(self, "affix_pool_layout"):
            return 0
        for affix_widget in self.iter_affix_widgets():
            if affix_widget.greater_checkbox.isChecked():
                want_greater_count += 1
        return want_greater_count

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
