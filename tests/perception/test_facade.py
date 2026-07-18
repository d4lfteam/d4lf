import sys

import pytest

from src import perception
from src.item.data.item_type import ItemType


def test_parse_item_text_is_typed_facade_for_terminal_items():
    item = perception.parse_item_text(["MALIGNANT HEART", "Legendary Boss Key"])

    assert item is not None
    assert item.item_type == ItemType.LairBossKey


@pytest.mark.skipif(sys.platform == "win32", reason="No-op adapter is selected on non-Windows only")
def test_start_connection_is_safe_without_windows_tts():
    perception.start_connection()

    assert perception.is_connected() is False
