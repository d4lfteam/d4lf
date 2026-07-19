from types import SimpleNamespace
from typing import Any, cast

import src.app.dashboard as dashboard_module
from src.app.dashboard import ActivityLogWidget
from src.settings import IS_HOTKEY_KEY


class _FakeLabel:
    def __init__(self, text: str) -> None:
        self._text = text

    def setObjectName(self, _name: str) -> None:  # ruff:ignore[invalid-function-name]
        pass

    def text(self) -> str:
        return self._text


class _FakeRowLayout:
    def __init__(self) -> None:
        self.widgets = []

    def setContentsMargins(self, *_args: int) -> None:  # ruff:ignore[invalid-function-name]
        pass

    def addWidget(self, widget: _FakeLabel) -> None:  # ruff:ignore[invalid-function-name]
        self.widgets.append(widget)

    def addStretch(self) -> None:  # ruff:ignore[invalid-function-name]
        pass


class _FakeGridLayout:
    def __init__(self) -> None:
        self.rows = []

    def count(self) -> int:
        return 0

    def addLayout(self, layout: _FakeRowLayout, row: int, column: int) -> None:  # ruff:ignore[invalid-function-name]
        self.rows.append((layout, row, column))


def test_hotkey_grid_builds_badges_from_hotkey_metadata(monkeypatch) -> None:
    monkeypatch.setattr(dashboard_module, "QHBoxLayout", _FakeRowLayout)
    monkeypatch.setattr(dashboard_module, "QLabel", _FakeLabel)
    options = SimpleNamespace(
        model_fields={"toggle": SimpleNamespace(json_schema_extra={IS_HOTKEY_KEY: "True"})},
        model_json_schema=lambda: {"properties": {"toggle": {"title": "Toggle Mode"}}},
        toggle="f1",
    )
    dashboard = cast(
        "Any", SimpleNamespace(hotkey_grid=_FakeGridLayout(), _config=SimpleNamespace(advanced_options=options))
    )

    ActivityLogWidget._setup_hotkey_grid(dashboard)

    assert len(dashboard.hotkey_grid.rows) == 1
    row, row_index, column = dashboard.hotkey_grid.rows[0]
    assert (row_index, column) == (0, 0)
    assert [widget.text() for widget in row.widgets] == ["F1", "Toggle Mode"]
