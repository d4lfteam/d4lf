# ruff:file-ignore[invalid-function-name]
from typing import Any, cast

from src.app.dashboard.drag import ActivityProfileDragMixin
from src.app.dashboard.profiles import ActivityProfileRowsMixin


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
    mixin = cast("Any", ActivityProfileRowsMixin())
    label = _VisibilityFake()
    button = _ButtonFake()

    mixin._toggle_row(label, button)

    assert label.isVisible()
    assert button.label == "▼"

    mixin._toggle_row(label, button)

    assert not label.isVisible()
    assert button.label == "▶"


def test_filter_profiles_matches_case_insensitively() -> None:
    mixin = cast("Any", ActivityProfileDragMixin())
    matching = _VisibilityFake()
    other = _VisibilityFake()
    mixin._rows = {"Alpha": matching, "Beta": other}
    mixin._update_zebra_striping = lambda: None

    mixin._filter_profiles("ALP")

    assert matching.isVisible()
    assert not other.isVisible()
