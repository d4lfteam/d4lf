import os
from types import SimpleNamespace
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.settings.widgets import QChestTabWidget

if TYPE_CHECKING:
    from collections.abc import Callable


def test_chest_tab_reset_callback_narrows_list_values():
    _app = QApplication.instance() or QApplication([])

    reset_callbacks: list[Callable[..., object]] = []

    def save_setting_value(*args: object) -> None:
        callback = args[-1]
        if not callable(callback):
            msg = "Expected a reset callback."
            raise TypeError(msg)
        reset_callbacks.append(callback)

    widget = QChestTabWidget(SimpleNamespace(max_stash_tabs=3), "section", "key", [0], save_setting_value)

    assert widget.all_checkboxes[0].isChecked()
    assert not widget.all_checkboxes[1].isChecked()

    widget._save_changes_on_box_change(widget.model, widget.section_header, widget.config_key)
    reset = reset_callbacks[-1]
    reset([1])

    assert not widget.all_checkboxes[0].isChecked()
    assert widget.all_checkboxes[1].isChecked()

    reset([2, "invalid"])
    assert not widget.all_checkboxes[0].isChecked()
    assert widget.all_checkboxes[1].isChecked()
