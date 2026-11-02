from typing import TYPE_CHECKING

from src.settings import GeneralModel
from src.settings.widgets import QChestTabWidget

if TYPE_CHECKING:
    from pydantic import BaseModel

    from src.settings.types import SettingValue


def test_chest_tab_widget_saves_checked_tabs(qapp) -> None:
    saved: list[tuple[str, str, SettingValue]] = []

    def save(_model: BaseModel, section: str, key: str, value: SettingValue) -> bool:
        saved.append((section, key, value))
        return True

    model = GeneralModel(max_stash_tabs=6)
    widget = QChestTabWidget(model, "general", "check_chest_tabs", [0], save)
    assert len(widget.all_checkboxes) == 6

    widget.all_checkboxes[2].setChecked(True)

    assert saved == [("general", "check_chest_tabs", "1,3")]

    widget.reset_values([1])
    assert [box.isChecked() for box in widget.all_checkboxes[:3]] == [False, True, False]
