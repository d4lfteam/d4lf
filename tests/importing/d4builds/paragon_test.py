import typing
from typing import cast, override

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from src.importing.d4builds import paragon as paragon_module
from src.importing.paragon import build_paragon_profile_payload

if typing.TYPE_CHECKING:
    from selenium.webdriver.support.relative_locator import RelativeBy

    from src.type_aliases import JsonValue


def test_parse_d4builds_paragon_boards_produces_valid_typed_payload_input() -> None:
    class _FakeTextNode(WebElement):
        def __init__(self, text: str) -> None:
            self._text = text

        @override
        def get_attribute(self, name: str) -> str:
            return self._text if name == "innerText" else ""

    class _FakeTile(WebElement):
        def __init__(self, class_name: str) -> None:
            self._class_name = class_name

        @override
        def get_attribute(self, name: str) -> str:
            return self._class_name if name == "class" else ""

    class _FakeBoardElement(WebElement):
        def __init__(self) -> None:
            self._attrs = {"data-board-id": "Paragon_Barb_00"}

        @override
        def find_element(self, by: str | By = By.ID, value: str | None = None) -> WebElement:
            if value is None:
                value = str(by)
            if value == "paragon__board__name":
                return _FakeTextNode("Starting Board")
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        @override
        def find_elements(self, by: str | By = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            if value == "paragon__board__name__glyph":
                return [_FakeTextNode("Glyph Name")]
            if value == "paragon__board__tile":
                return [_FakeTile("paragon__board__tile r2 c10 active enabled")]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        @override
        def get_attribute(self, name: str) -> str:
            return "transform: rotate(90deg);" if name == "style" else ""

    class _FakeDriver(WebDriver):
        def __init__(self) -> None:
            pass

        @override
        def execute_script(self, script: str, *args: JsonValue) -> JsonValue:
            return {"data-board-id": "Paragon_Barb_00"}

        @override
        def find_elements(self, by: str | By | RelativeBy = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            if value == "paragon__board":
                return [_FakeBoardElement()]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

    boards = paragon_module._parse_d4builds_paragon_boards(_FakeDriver(), class_slug="barbarian")
    payload = build_paragon_profile_payload("Build Name", "https://example.invalid", boards)

    board = payload.paragon_boards_list[0][0]
    assert board.name == "barbarian-paragon-barb-00"
    assert board.rotation == "90°"
    assert board.nodes.count(True) == 1


@pytest.mark.parametrize(("rotation_deg", "expected_index"), [(0, 30), (90, 208), (180, 410), (270, 232)])
def test_parse_d4builds_paragon_boards_keeps_supported_rotation_transform_behavior(
    rotation_deg: int, expected_index: int
) -> None:
    class _FakeTextNode(WebElement):
        def __init__(self, text: str) -> None:
            self._text = text

        @override
        def get_attribute(self, name: str) -> str:
            return self._text if name == "innerText" else ""

    class _FakeTile(WebElement):
        def __init__(self, class_name: str) -> None:
            self._class_name = class_name

        @override
        def get_attribute(self, name: str) -> str:
            return self._class_name if name == "class" else ""

    class _FakeBoardElement(WebElement):
        def __init__(self) -> None:
            self._attrs = {"data-board-id": "Paragon_Barb_00"}

        @override
        def find_element(self, by: str | By = By.ID, value: str | None = None) -> WebElement:
            if value is None:
                value = str(by)
            if value == "paragon__board__name":
                return _FakeTextNode("Starting Board")
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        @override
        def find_elements(self, by: str | By = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            if value == "paragon__board__name__glyph":
                return []
            if value == "paragon__board__tile":
                return [_FakeTile("paragon__board__tile r2 c10 active enabled")]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        @override
        def get_attribute(self, name: str) -> str:
            if name == "style":
                return f"transform: rotate({rotation_deg}deg);"
            return ""

    class _FakeDriver(WebDriver):
        def __init__(self) -> None:
            pass

        @override
        def execute_script(self, script: str, *args: JsonValue) -> JsonValue:
            return {"data-board-id": "Paragon_Barb_00"}

        @override
        def find_elements(self, by: str | By | RelativeBy = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            if value == "paragon__board":
                return [_FakeBoardElement()]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

    boards = paragon_module._parse_d4builds_paragon_boards(_FakeDriver(), class_slug="barbarian")
    board = boards[0][0]
    nodes = cast("list[bool]", board["Nodes"])

    assert board["Rotation"] == f"{rotation_deg}°"
    assert nodes.count(True) == 1
    assert nodes[expected_index] is True


def test_parse_d4builds_paragon_boards_uses_question_mark_fallback_for_unsupported_rotation() -> None:
    class _FakeTextNode(WebElement):
        def __init__(self, text: str) -> None:
            self._text = text

        @override
        def get_attribute(self, name: str) -> str:
            return self._text if name == "innerText" else ""

    class _FakeTile(WebElement):
        def __init__(self, class_name: str) -> None:
            self._class_name = class_name

        @override
        def get_attribute(self, name: str) -> str:
            return self._class_name if name == "class" else ""

    class _FakeBoardElement(WebElement):
        def __init__(self) -> None:
            self._attrs = {"data-board-id": "Paragon_Barb_00"}

        @override
        def find_element(self, by: str | By = By.ID, value: str | None = None) -> WebElement:
            if value is None:
                value = str(by)
            if value == "paragon__board__name":
                return _FakeTextNode("Starting Board")
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        @override
        def find_elements(self, by: str | By = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            if value == "paragon__board__name__glyph":
                return []
            if value == "paragon__board__tile":
                return [_FakeTile("paragon__board__tile r2 c10 active enabled")]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

        @override
        def get_attribute(self, name: str) -> str:
            return "transform: rotate(45deg);" if name == "style" else ""

    class _FakeDriver(WebDriver):
        def __init__(self) -> None:
            pass

        @override
        def execute_script(self, script: str, *args: JsonValue) -> JsonValue:
            return {"data-board-id": "Paragon_Barb_00"}

        @override
        def find_elements(self, by: str | By | RelativeBy = By.ID, value: str | None = None) -> list[WebElement]:
            if value is None:
                value = str(by)
            if value == "paragon__board":
                return [_FakeBoardElement()]
            msg = f"unexpected selector: {value}"
            raise AssertionError(msg)

    boards = paragon_module._parse_d4builds_paragon_boards(_FakeDriver(), class_slug="barbarian")

    assert boards[0][0]["Rotation"] == "?°"
