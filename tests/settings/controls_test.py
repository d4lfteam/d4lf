import os
from typing import TYPE_CHECKING

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pydantic import BaseModel
from PyQt6.QtWidgets import QCheckBox, QLineEdit, QSpinBox

from src.settings.controls import create_control, reset_control

if TYPE_CHECKING:
    from src.settings.types import SettingValue


class _Model(BaseModel):
    enabled: bool = False
    count: int = 1
    name: str = "a"


def test_controls_save_edits_and_show_reset_values(qapp) -> None:
    saved: list[tuple[str, SettingValue]] = []

    def save(_model: BaseModel, _section: str, key: str, value: SettingValue) -> bool:
        saved.append((key, value))
        return True

    model = _Model()
    checkbox = create_control(model, "s", "enabled", model.enabled, False, save)
    spin_box = create_control(model, "s", "count", model.count, False, save)
    line_edit = create_control(model, "s", "name", model.name, False, save)
    assert isinstance(checkbox, QCheckBox)
    assert isinstance(spin_box, QSpinBox)
    assert isinstance(line_edit, QLineEdit)

    checkbox.setChecked(True)
    spin_box.setValue(5)
    assert saved == [("enabled", "True"), ("count", 5)]

    reset_control(line_edit, "b")
    assert line_edit.text() == "b"
