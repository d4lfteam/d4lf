# ruff:file-ignore[invalid-function-name]
from typing import TYPE_CHECKING, cast

from src.app.dashboard.drag import ActivityProfileDragMixin
from src.app.dashboard.profiles import ActivityProfileRowsMixin

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QLabel, QPushButton

    from src.app.dashboard.core import ActivityLogWidget


class _VisibilityFake:
    def __init__(self) -> None:
        self.visible = False

    def isVisible(self) -> bool:
        return self.visible

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class _ButtonFake:
    def __init__(self) -> None:
        self.label = "▶"

    def setText(self, label: str) -> None:
        self.label = label


def test_toggle_row_updates_visibility_and_button_label() -> None:
    mixin = cast("ActivityLogWidget", ActivityProfileRowsMixin())
    label = _VisibilityFake()
    button = _ButtonFake()

    ActivityProfileRowsMixin._toggle_row(mixin, cast("QLabel", label), cast("QPushButton", button))

    assert label.isVisible()
    assert button.label == "▼"

    ActivityProfileRowsMixin._toggle_row(mixin, cast("QLabel", label), cast("QPushButton", button))

    assert not label.isVisible()
    assert button.label == "▶"


def test_filter_profiles_matches_case_insensitively() -> None:
    mixin = cast("ActivityLogWidget", ActivityProfileDragMixin())
    matching = _VisibilityFake()
    other = _VisibilityFake()
    mixin.__dict__["_rows"] = {"Alpha": matching, "Beta": other}
    mixin.__dict__["_update_zebra_striping"] = lambda: None

    mixin._filter_profiles("ALP")

    assert matching.isVisible()
    assert not other.isVisible()
