from typing import TYPE_CHECKING, override

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.dataloader import Dataloader
from src.gui.models.collapsible_widget import Container
from src.gui.models.dialog import (
    CreateCharmOrSeal,
    DeleteAffixPool,
    MinGreaterDialog,
    MinPercentDialog,
    RarityPicker,
    SetPicker,
    rarity_summary,
)
from src.gui.models.tab_group_widget import TabGroupWidget
from src.gui.profile_editor.affixes_tab import UNIQUE_ASPECTS_TITLE, AffixPoolWidget, AffixWidget, UniqueAspectWidget
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicSealFilterModel,
    SealFilterModel,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from pydantic import RootModel

CHARMS_TABNAME = "Charms"
SEALS_TABNAME = "Seals"


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


class BaseGroupEditor[ConfigT: CharmFilterModel | SealFilterModel](QWidget):
    """Shared base editor class for single-named filters (Charms and Seals)."""

    def __init__(self, dynamic_filter: RootModel[dict[str, ConfigT]], is_charm: bool, parent=None):
        super().__init__(parent)
        self.is_charm = is_charm
        self.type_prefix = "charm" if is_charm else "seal"
        self.settings = QSettings("d4lf", "profile_editor")
        if len(dynamic_filter.root) != 1:
            msg = "BaseGroupEditor requires a single-key dynamic filter model."
            raise ValueError(msg)
        self.item_name, self.config = next(iter(dynamic_filter.root.items()))

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

    def setup_ui(self):
        """Build the common UI layout structure."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        general_form = QFormLayout()

        # Rarities (Common)
        self.add_rarity_row(general_form)

        # Custom fields (Subclass hook - e.g. Sets for Charms)
        self.add_custom_general_fields(general_form)

        # Min Greater Affixes & Auto Sync (Common)
        self.add_min_greater_row(general_form)

        self.content_layout.addLayout(general_form)
        self.create_unique_aspect_container()

        # Affix Pool container (Common)
        self.add_affix_pool_section()

        scroll_area.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        QTimer.singleShot(100, self.affix_pool_container.expand)

    def add_rarity_row(self, general_form: QFormLayout):
        """Add the rarity picker row to the form."""
        self.rarity_line_edit = _create_readonly_line_edit()
        self.refresh_rarity_summary()

        rarity_layout = QHBoxLayout()
        rarity_layout.addWidget(self.rarity_line_edit)
        edit_rarities_btn = QPushButton("...")
        edit_rarities_btn.setMaximumWidth(40)
        edit_rarities_btn.clicked.connect(self.edit_rarities)
        rarity_layout.addWidget(edit_rarities_btn)
        rarity_layout.addStretch()
        general_form.addRow("Rarities:", rarity_layout)

    def add_min_greater_row(self, general_form: QFormLayout):
        """Add the Min Greater Affixes and Auto Sync controls to the form."""
        min_greater_layout = QHBoxLayout()

        self.min_greater = QSpinBox()
        self.min_greater.setValue(self.config.min_greater_affix_count)
        self.min_greater.setMaximum(4)
        self.min_greater.setMinimum(0)
        self.min_greater.setMaximumWidth(80)
        self.min_greater.setToolTip(
            "Minimum number of checked affixes that must be Greater Affixes.\n"
            "0 = Accept items even without GAs (for leveling)\n"
            "1-4 = At least this many checked affixes must be GA"
        )
        self.min_greater.valueChanged.connect(self.update_min_greater_affix)

        self.auto_sync_checkbox = _create_auto_sync_checkbox()
        self.auto_sync_checkbox.setChecked(
            self.settings.value(f"auto_sync_ga_{self.type_prefix}_{self.item_name}", defaultValue=False, type=bool)
        )
        self.auto_sync_checkbox.stateChanged.connect(self.toggle_auto_sync)

        self.greater_count_label = QLabel()
        self.greater_count_label.setProperty("greaterCountLabel", True)  # noqa: FBT003
        _refresh_widget_style(self.greater_count_label)
        self.update_greater_count_label()

        min_greater_layout.addWidget(self.min_greater)
        min_greater_layout.addWidget(self.auto_sync_checkbox)
        min_greater_layout.addWidget(self.greater_count_label)
        min_greater_layout.addStretch()

        self.min_greater.setEnabled(not self.auto_sync_checkbox.isChecked())

        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setProperty("autoSyncSpin", True)  # noqa: FBT003
            _refresh_widget_style(self.min_greater)

        general_form.addRow("Min Greater Affixes:", min_greater_layout)

    def add_affix_pool_section(self):
        """Add the affix pool section to the layout."""
        pool_btn_layout = QHBoxLayout()
        add_affix_pool_btn = QPushButton("Add Affix Pool")
        add_affix_pool_btn.clicked.connect(self.add_affix_pool)
        remove_affix_pool_btn = QPushButton("Remove Affix Pool")
        remove_affix_pool_btn.clicked.connect(lambda: self.remove_selected(self.affix_pool_layout))

        pool_btn_layout.addWidget(add_affix_pool_btn)
        pool_btn_layout.addWidget(remove_affix_pool_btn)

        self.affix_pool_container = Container("Affix Pool")
        self.affix_pool_layout = QVBoxLayout(self.affix_pool_container.content_widget)
        self.affix_pool_container.first_expansion.connect(self.init_affix_pool)

        self.content_layout.addWidget(self.affix_pool_container)
        self.content_layout.addLayout(pool_btn_layout)

    def add_custom_general_fields(self, general_form: QFormLayout) -> None:
        """Stub method for subclasses to add their unique general fields."""

    # --- Unique Aspects ---

    def _unique_aspects_title(self) -> str:
        aspect_names = ", ".join(unique_aspect.name for unique_aspect in self.config.unique_aspect) or "None"
        return f"{UNIQUE_ASPECTS_TITLE} - {aspect_names}"

    def refresh_unique_aspects_title(self):
        self.unique_aspect_container.header.set_name(self._unique_aspects_title())

    def create_unique_aspect_container(self):
        container = Container(UNIQUE_ASPECTS_TITLE)
        layout = QVBoxLayout(container.content_widget)

        self.unique_aspect_list = QListWidget()
        self.unique_aspect_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.unique_aspect_list.setMinimumHeight(150)
        self.init_unique_aspects()

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Aspect")
        add_btn.clicked.connect(self.add_unique_aspect)
        remove_btn = QPushButton("Remove Aspect")
        remove_btn.clicked.connect(self.remove_unique_aspect)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)

        layout.addWidget(self.unique_aspect_list)
        layout.addLayout(btn_layout)

        self.unique_aspect_container = container
        self.content_layout.addWidget(container)

    def init_unique_aspects(self):
        for unique_aspect in self.config.unique_aspect:
            self.add_unique_aspect_item(unique_aspect)

    def add_unique_aspect_item(self, unique_aspect: AspectUniqueFilterModel):
        item = QListWidgetItem()
        allowed = sorted([k for k in Dataloader().aspect_unique_dict if k.startswith(f"{self.type_prefix}_of")])
        widget = UniqueAspectWidget(unique_aspect, allowed_aspects=allowed, parent=self)
        item_size = widget.sizeHint()
        item_size.setWidth(850)
        item.setSizeHint(item_size)
        self.unique_aspect_list.addItem(item)
        self.unique_aspect_list.setItemWidget(item, widget)

    def add_unique_aspect(self):
        if self.is_charm:
            if not isinstance(self.config, CharmFilterModel):
                msg = "Charm editors require a charm filter model."
                raise TypeError(msg)
            if self.config.set:
                QMessageBox.warning(self, "Warning", "Cannot add unique aspects when sets are selected.")
                return
        existing_names = {unique_aspect.name for unique_aspect in self.config.unique_aspect}
        allowed = [k for k in Dataloader().aspect_unique_dict if k.startswith(f"{self.type_prefix}_of")]
        for aspect_name in allowed:
            if aspect_name in existing_names:
                continue
            new_unique_aspect = AspectUniqueFilterModel(name=aspect_name, value=None)
            self.config.unique_aspect.append(new_unique_aspect)
            self.add_unique_aspect_item(new_unique_aspect)
            break
        self.refresh_unique_aspects_title()

    def remove_unique_aspect(self):
        row = self.unique_aspect_list.currentRow()
        if row != -1:
            self.unique_aspect_list.takeItem(row)
            del self.config.unique_aspect[row]
        self.refresh_unique_aspects_title()

    # --- Affix Pool ---

    def init_affix_pool(self):
        """Initialize affix pool content on first expansion."""
        for pool in self.config.affix_pool:
            self.add_affix_pool_item(pool)
        QTimer.singleShot(50, self.update_greater_count_label)

    def add_affix_pool_item(self, pool: AffixFilterCountModel):
        nb_count = self.affix_pool_layout.count()
        container = Container(f"Count {nb_count}", color_background=True)
        container_layout = QVBoxLayout(container.content_widget)
        widget = AffixPoolWidget(pool, self)
        container_layout.addWidget(widget)
        self.affix_pool_layout.addWidget(container)
        QTimer.singleShot(50, container.expand)

    def add_affix_pool(self):
        affix_dict = Dataloader().charm_affix_dict if self.is_charm else Dataloader().seal_affix_dict
        default_affix_name = next(iter(affix_dict.keys()), "")
        default_affix = AffixFilterModel(name=default_affix_name, value=None)
        new_pool = AffixFilterCountModel(count=[default_affix], min_count=1, max_count=3)
        self.config.affix_pool.append(new_pool)
        self.add_affix_pool_item(new_pool)

    def remove_selected(self, layout_widget: QVBoxLayout):
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

    def update_affix_pool_names(self, layout_widget: QVBoxLayout):
        for i in range(layout_widget.count()):
            item = layout_widget.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if isinstance(widget, Container):
                widget.header.set_name(f"Count {i}")

    # --- Rarities ---

    def edit_rarities(self):
        dialog = RarityPicker(self, self.config.rarities)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.rarities = dialog.get_selected_rarities()
            self.refresh_rarity_summary()

    def refresh_rarity_summary(self):
        self.rarity_line_edit.setText(rarity_summary(self.config.rarities))

    # --- Auto Sync minGreaterAffixCount ---

    def update_min_greater_affix(self):
        self.config.min_greater_affix_count = self.min_greater.value()

    def toggle_auto_sync(self, state):
        is_auto_sync = state == Qt.CheckState.Checked.value
        self.settings.setValue(f"auto_sync_ga_{self.type_prefix}_{self.item_name}", is_auto_sync)
        self.min_greater.setEnabled(not is_auto_sync)

        if is_auto_sync:
            self.min_greater.setProperty("autoSyncSpin", True)  # noqa: FBT003
            _refresh_widget_style(self.min_greater)
            self.affix_pool_container.expand()
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)
            self.update_greater_count_label()
        else:
            self.min_greater.setProperty("autoSyncSpin", False)  # noqa: FBT003
            _refresh_widget_style(self.min_greater)

    def sync_min_greater_from_checkboxes(self):
        if self.auto_sync_checkbox.isChecked():
            count = self.count_want_greater_affixes()
            self.min_greater.setValue(count)

    def _ensure_pool_widgets_initialized(self):
        was_visible = self.affix_pool_container.content_widget.isVisible()
        if self.affix_pool_container.header.first_expansion:
            self.affix_pool_container.expand()
            if not was_visible:
                self.affix_pool_container.collapse()

    def iter_affix_widgets(self):
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

    def count_want_greater_affixes(self) -> int:
        want_greater_count = 0
        if not hasattr(self, "affix_pool_layout"):
            return 0
        for affix_widget in self.iter_affix_widgets():
            if affix_widget.greater_checkbox.isChecked():
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

    def convert_all_to_min_percent_of_affix(self, percent: int):
        for affix_widget in self.iter_affix_widgets():
            affix_widget.set_min_percent(percent, convert_mode=True)


class CharmGroupEditor(BaseGroupEditor[CharmFilterModel]):
    """Editor widget for a single named charm filter."""

    def __init__(self, dynamic_filter: DynamicCharmFilterModel, parent=None):
        super().__init__(dynamic_filter, is_charm=True, parent=parent)
        self.setup_ui()

    @override
    def add_custom_general_fields(self, general_form: QFormLayout) -> None:
        """Add charm-specific set selection row."""
        self.set_line_edit = _create_readonly_line_edit()
        self.refresh_set_summary()

        set_layout = QHBoxLayout()
        set_layout.addWidget(self.set_line_edit)
        edit_sets_btn = QPushButton("...")
        edit_sets_btn.setMaximumWidth(40)
        edit_sets_btn.clicked.connect(self.edit_sets)
        set_layout.addWidget(edit_sets_btn)
        set_layout.addStretch()
        general_form.addRow("Sets:", set_layout)

    def edit_sets(self):
        if self.config.unique_aspect:
            QMessageBox.warning(self, "Warning", "Cannot select sets when unique aspects are defined.")
            return
        dialog = SetPicker(parent=self, selected_sets=self.config.set)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.set = dialog.get_selected_sets()
            self.refresh_set_summary()

    def refresh_set_summary(self):
        self.set_line_edit.setText(_set_summary(self.config.set))


class SealGroupEditor(BaseGroupEditor[SealFilterModel]):
    """Editor widget for a single named seal filter."""

    def __init__(self, dynamic_filter: DynamicSealFilterModel, parent=None):
        super().__init__(dynamic_filter, is_charm=False, parent=parent)
        self.setup_ui()


class BaseCharmsSealsTab[ModelT, ConfigT](TabGroupWidget[ModelT]):
    """Shared base class for Charms and Seals tabs to manage a list of single-key models."""

    def __init__(
        self,
        models: list[ModelT],
        is_charm: bool,
        model_items: Callable[[ModelT], Iterable[tuple[str, ConfigT]]],
        model_factory: Callable[[str, ConfigT], ModelT],
        editor_factory: Callable[[ModelT], QWidget],
        model_type: type[ModelT],
        tab_label_factory: Callable[[ModelT], str],
        parent=None,
    ):
        self.is_charm = is_charm
        self.type_prefix = "charm" if is_charm else "seal"
        self._model_items = model_items
        self._model_factory = model_factory
        self._editor_factory = editor_factory
        self._model_type = model_type
        self._tab_label_factory = tab_label_factory
        super().__init__(models, parent)

    @override
    def prepare_models(self) -> None:
        """Split any multi-key dynamic models into single-key models, warning on duplicate names."""
        item_names: list[str] = []
        normalized_models: list[ModelT] = []
        for group in self.models:
            for item_name, config in self._model_items(group):
                if item_name in item_names:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        f"{self.type_prefix.capitalize()} name already exists, please rename {item_name} in the profile file.",
                    )
                    continue
                item_names.append(item_name)
                normalized_models.append(self._model_factory(item_name, config))
        self.models.clear()
        self.models.extend(normalized_models)

    @override
    def create_editor(self, model: ModelT) -> QWidget:
        return self._editor_factory(model)

    @override
    def tab_label(self, model: ModelT, index: int) -> str:
        return self._tab_label_factory(model)

    @override
    def create_model(self) -> ModelT | None:
        existing_names = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        dialog = CreateCharmOrSeal(existing_names, is_charm=self.is_charm, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        model = dialog.get_value()
        if not isinstance(model, self._model_type):
            msg = f"{self.type_prefix.capitalize()} creation returned the wrong model type."
            raise TypeError(msg)
        return model

    @override
    def toolbar_name(self) -> str:
        return f"{self.type_prefix.capitalize()}sToolBar"

    @override
    def add_button_text(self) -> str:
        return f"Create {self.type_prefix.capitalize()}"

    @override
    def remove_button_text(self) -> str:
        return f"Remove {self.type_prefix.capitalize()}"

    @override
    def toolbar_buttons(self) -> list[QPushButton]:
        buttons = super().toolbar_buttons()

        set_all_min_greater_affix_button = QPushButton("Set All Min GAs (Excludes Auto Synced Items)")
        set_all_min_greater_affix_button.clicked.connect(self.set_all_min_greater_affix)
        convert_all_to_min_percent_button = QPushButton("Convert All To Min %")
        convert_all_to_min_percent_button.clicked.connect(self.convert_all_to_min_percent_of_affix)

        buttons.extend([set_all_min_greater_affix_button, convert_all_to_min_percent_button])
        return buttons

    def set_all_min_greater_affix(self):
        dialog = MinGreaterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            min_greater_affix = dialog.get_value()
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if not isinstance(tab, BaseGroupEditor) or tab.auto_sync_checkbox.isChecked():
                    continue
                tab.min_greater.setValue(min_greater_affix)
                tab.update_min_greater_affix()

    def convert_all_to_min_percent_of_affix(self):
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, BaseGroupEditor):
            dialog = MinPercentDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                current_tab.convert_all_to_min_percent_of_affix(dialog.get_value())


class CharmsTab(BaseCharmsSealsTab[DynamicCharmFilterModel, CharmFilterModel]):
    def __init__(self, charms_model: list[DynamicCharmFilterModel], parent=None):
        super().__init__(
            charms_model,
            is_charm=True,
            model_items=lambda model: model.root.items(),
            model_factory=lambda item_name, config: DynamicCharmFilterModel(root={item_name: config}),
            editor_factory=CharmGroupEditor,
            model_type=DynamicCharmFilterModel,
            tab_label_factory=lambda model: next(iter(model.root)),
            parent=parent,
        )


class SealsTab(BaseCharmsSealsTab[DynamicSealFilterModel, SealFilterModel]):
    def __init__(self, seals_model: list[DynamicSealFilterModel], parent=None):
        super().__init__(
            seals_model,
            is_charm=False,
            model_items=lambda model: model.root.items(),
            model_factory=lambda item_name, config: DynamicSealFilterModel(root={item_name: config}),
            editor_factory=SealGroupEditor,
            model_type=DynamicSealFilterModel,
            tab_label_factory=lambda model: next(iter(model.root)),
            parent=parent,
        )


# --- Common Helpers ---


def _create_readonly_line_edit():
    line_edit = QLineEdit()
    line_edit.setReadOnly(True)
    line_edit.setMinimumWidth(360)
    line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return line_edit


def _create_auto_sync_checkbox():
    checkbox = QCheckBox("Auto Sync")
    checkbox.setToolTip(
        "When checked: Min Greater Affixes automatically matches the number of affixes marked as 'want greater'\n"
        "When unchecked: You can manually set Min Greater Affixes to any value"
    )
    return checkbox


def _refresh_widget_style(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
