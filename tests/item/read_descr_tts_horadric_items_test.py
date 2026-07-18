from typing import TYPE_CHECKING

import pytest

from src.item.data.item_type import ItemType
from tests.item.read_descr_tts_cases_horadric_and_equipment import items as horadric_and_equipment_items

if TYPE_CHECKING:
    from src.item.models import Item

from src.perception import parse_item_text

HORADRIC_TYPES = {ItemType.HoradricSeal, ItemType.Charm}
items = [item for item in horadric_and_equipment_items if item[1].item_type in HORADRIC_TYPES]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_horadric_items(input_item: list[str], expected_item: Item):
    item = parse_item_text(input_item)
    assert item == expected_item
