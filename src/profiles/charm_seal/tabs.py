from typing import TYPE_CHECKING, override

from PyQt6.QtWidgets import QCheckBox, QDialog, QLineEdit, QMessageBox, QPushButton, QSizePolicy, QWidget

from src.profiles import CharmFilterModel, DynamicCharmFilterModel, DynamicSealFilterModel, SealFilterModel
from src.profiles.charm_seal.dialogs import CreateCharmOrSeal
from src.profiles.charm_seal.group import BaseGroupEditor, CharmGroupEditor, SealGroupEditor
from src.profiles.editor.dialogs import MinGreaterDialog, MinPercentDialog
from src.profiles.editor.tabs import TabGroupWidget

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


CHARMS_TABNAME = "Charms"
SEALS_TABNAME = "Seals"


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


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
