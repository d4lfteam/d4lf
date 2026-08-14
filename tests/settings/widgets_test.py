import os
from typing import TYPE_CHECKING, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pydantic import BaseModel
from PyQt6.QtWidgets import QApplication

from src.settings.widgets import QChestTabWidget

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.settings.types import SettingValue

type SaveArgument = BaseModel | str | Callable[[SettingValue], None]


class _ChestModel(BaseModel):
    max_stash_tabs: int = 3


def test_chest_tab_reset_callback_narrows_list_values() -> None:
    _app = QApplication.instance() or QApplication([])

    reset_callbacks: list[Callable[[SettingValue], None]] = []

    def save_setting_value(*args: SaveArgument) -> bool:
        callback = args[-1]
        if not callable(callback):
            msg = "Expected a reset callback."
            raise TypeError(msg)
        reset_callbacks.append(cast("Callable[[SettingValue], None]", callback))
        return True

    widget = QChestTabWidget(_ChestModel(), "section", "key", [0], save_setting_value)

    assert widget.all_checkboxes[0].isChecked()
    assert not widget.all_checkboxes[1].isChecked()

    widget._save_changes_on_box_change(widget.model, widget.section_header, widget.config_key)
    reset = reset_callbacks[-1]
    reset([1])

    assert not widget.all_checkboxes[0].isChecked()
    assert widget.all_checkboxes[1].isChecked()

    reset(cast("SettingValue", [2, "invalid"]))
    assert not widget.all_checkboxes[0].isChecked()
    assert widget.all_checkboxes[1].isChecked()
