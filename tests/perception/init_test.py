import sys

import pytest

from src import perception
from src.item import ItemType


def test_perception_facade_exposes_typed_item_and_geometry_operations() -> None:
    item = perception.parse_item_text(["MALIGNANT HEART", "Legendary Boss Key"])

    assert item is not None
    assert item.original_name == "MALIGNANT HEART"
    assert perception.center_of_roi((0, 0, 10, 10)) == (5, 5)


def test_parse_item_text_is_typed_facade_for_terminal_items():
    item = perception.parse_item_text(["MALIGNANT HEART", "Legendary Boss Key"])

    assert item is not None
    assert item.item_type == ItemType.LairBossKey


def test_capture_is_the_callable_public_facade():
    assert callable(perception.capture)


@pytest.mark.skipif(sys.platform == "win32", reason="No-op adapter is selected on non-Windows only")
def test_start_connection_is_safe_without_windows_tts():
    perception.start_connection()

    assert perception.is_connected() is False
