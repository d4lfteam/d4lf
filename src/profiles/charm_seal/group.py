from typing import TYPE_CHECKING, cast, override

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
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.profiles import CharmFilterModel, DynamicCharmFilterModel, DynamicSealFilterModel, SealFilterModel
from src.profiles.charm_seal.dialogs import SetPicker
from src.profiles.charm_seal.general import _CharmSealGeneralMixin
from src.profiles.charm_seal.pools import _CharmSealPoolsMixin
from src.profiles.editor.helpers import create_readonly_line_edit

if TYPE_CHECKING:
    from pydantic import RootModel

    from src.profiles.charm_seal.general import CharmSealEditor
    from src.profiles.editor.container import Container

CHARMS_TABNAME = "Charms"
SEALS_TABNAME = "Seals"


def _set_summary(sets: list[str]) -> str:
    if not sets:
        return "No sets selected"
    return ", ".join(sets)


class BaseGroupEditor[ConfigT: CharmFilterModel | SealFilterModel](
    _CharmSealGeneralMixin, _CharmSealPoolsMixin, QWidget
):
    config: ConfigT
    content_layout: QVBoxLayout
    item_name: str
    type_prefix: str
    is_charm: bool
    settings: QSettings
    rarity_line_edit: QLineEdit
    min_greater: QSpinBox
    auto_sync_checkbox: QCheckBox
    greater_count_label: QLabel
    affix_pool_container: Container
    affix_pool_layout: QVBoxLayout
    unique_aspect_container: Container
    unique_aspect_list: QListWidget

    """Shared base editor class for single-named filters (Charms and Seals)."""

    def __init__(
        self, dynamic_filter: RootModel[dict[str, ConfigT]], is_charm: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.is_charm = is_charm
        self.type_prefix = "charm" if is_charm else "seal"
        self.settings = QSettings("d4lf", "profile_editor")
        if len(dynamic_filter.root) != 1:
            msg = "BaseGroupEditor requires a single-key dynamic filter model."
            raise ValueError(msg)
        self.item_name, self.config = next(iter(dynamic_filter.root.items()))

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

    def setup_ui(self) -> None:
        """Build the common UI layout structure."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        general_form = QFormLayout()
        editor = cast("CharmSealEditor", self)

        # Rarities (Common)
        editor.add_rarity_row(general_form)

        # Custom fields (Subclass hook - e.g. Sets for Charms)
        editor.add_custom_general_fields(general_form)

        # Min Greater Affixes & Auto Sync (Common)
        editor.add_min_greater_row(general_form)

        self.content_layout.addLayout(general_form)
        editor.create_unique_aspect_container()

        # Affix Pool container (Common)
        editor.add_affix_pool_section()

        scroll_area.setWidget(content_widget)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        QTimer.singleShot(100, self.affix_pool_container.expand)


class CharmGroupEditor(BaseGroupEditor[CharmFilterModel]):
    """Editor widget for a single named charm filter."""

    def __init__(self, dynamic_filter: DynamicCharmFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(dynamic_filter, is_charm=True, parent=parent)
        self.setup_ui()

    @override
    def add_custom_general_fields(self, general_form: QFormLayout) -> None:
        """Add charm-specific set selection row."""
        self.set_line_edit = create_readonly_line_edit()
        self.refresh_set_summary()

        set_layout = QHBoxLayout()
        set_layout.addWidget(self.set_line_edit)
        edit_sets_btn = QPushButton("...")
        edit_sets_btn.setMaximumWidth(40)
        edit_sets_btn.clicked.connect(self.edit_sets)
        set_layout.addWidget(edit_sets_btn)
        set_layout.addStretch()
        general_form.addRow("Sets:", set_layout)

    def edit_sets(self) -> None:
        if self.config.unique_aspect:
            QMessageBox.warning(self, "Warning", "Cannot select sets when unique aspects are defined.")
            return
        dialog = SetPicker(parent=self, selected_sets=self.config.set)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config.set = dialog.get_selected_sets()
            self.refresh_set_summary()

    def refresh_set_summary(self) -> None:
        self.set_line_edit.setText(_set_summary(self.config.set))


class SealGroupEditor(BaseGroupEditor[SealFilterModel]):
    """Editor widget for a single named seal filter."""

    def __init__(self, dynamic_filter: DynamicSealFilterModel, parent: QWidget | None = None) -> None:
        super().__init__(dynamic_filter, is_charm=False, parent=parent)
        self.setup_ui()
