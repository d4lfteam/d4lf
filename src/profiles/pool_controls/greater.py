from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QWidget

from src.profiles.editor.helpers import create_auto_sync_checkbox, refresh_widget_style

if TYPE_CHECKING:
    from src.profiles import CharmFilterModel, ItemFilterModel, SealFilterModel

MAX_GREATER_AFFIXES = 4


def _count_text(count: int) -> str:
    if count == 0:
        return "(no greater affixes marked)"
    if count == 1:
        return "(1 greater affix marked)"
    return f"({count} greater affixes marked)"


class GreaterAffixControls(QWidget):
    """Min Greater Affixes spin box whose Auto Sync mode follows the affixes marked as greater.

    The auto-sync state is UI-only and stored in QSettings under ``auto_sync_ga_{settings_key}``.
    """

    def __init__(
        self,
        config: ItemFilterModel | CharmFilterModel | SealFilterModel,
        settings_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._settings = QSettings("d4lf", "profile_editor")
        self._settings_key = f"auto_sync_ga_{settings_key}"

        self.min_greater = QSpinBox()
        self.min_greater.setRange(0, MAX_GREATER_AFFIXES)
        self.min_greater.setValue(config.min_greater_affix_count)
        self.min_greater.setMaximumWidth(80)
        self.min_greater.setToolTip(
            "Minimum number of checked affixes that must be Greater Affixes.\n"
            "0 = Accept items even without GAs (for leveling)\n"
            "1-4 = At least this many checked affixes must be GA"
        )
        self.min_greater.valueChanged.connect(self._store_min_greater)

        self.auto_sync_checkbox = create_auto_sync_checkbox()
        self.auto_sync_checkbox.setChecked(self._settings.value(self._settings_key, defaultValue=False, type=bool))
        self.auto_sync_checkbox.toggled.connect(self._toggle_auto_sync)

        self.count_label = QLabel(_count_text(self._count_greater()))
        self.count_label.setProperty("greaterCountLabel", True)  # ruff:ignore[FBT003]
        refresh_widget_style(self.count_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.min_greater)
        layout.addWidget(self.auto_sync_checkbox)
        layout.addWidget(self.count_label)
        layout.addStretch()
        self._apply_auto_sync_style()

    def refresh(self) -> None:
        """Update the marked-greater count and, in Auto Sync mode, the min greater value."""
        count = self._count_greater()
        self.count_label.setText(_count_text(count))
        if self.auto_sync_checkbox.isChecked():
            self.min_greater.setValue(count)

    def set_min_greater(self, value: int) -> None:
        """Set the min greater value unless Auto Sync controls it."""
        if not self.auto_sync_checkbox.isChecked():
            self.min_greater.setValue(value)

    def _count_greater(self) -> int:
        return sum(affix.want_greater for pool in self._config.affix_pool for affix in pool.count)

    def _store_min_greater(self, value: int) -> None:
        self._config.min_greater_affix_count = value

    def _toggle_auto_sync(self, checked: bool) -> None:
        self._settings.setValue(self._settings_key, checked)
        self._apply_auto_sync_style()
        self.refresh()

    def _apply_auto_sync_style(self) -> None:
        is_auto_sync = self.auto_sync_checkbox.isChecked()
        self.min_greater.setEnabled(not is_auto_sync)
        self.min_greater.setProperty("autoSyncSpin", is_auto_sync)
        refresh_widget_style(self.min_greater)
