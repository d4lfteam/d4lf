from typing import TYPE_CHECKING

import pytest

from src.item.data.item_type import ItemType
from tests.item.read_descr_tts_cases_bloodied_items import items as bloodied_items
from tests.item.read_descr_tts_cases_horadric_and_equipment import items as horadric_and_equipment_items
from tests.item.read_descr_tts_cases_sanctified_and_sigils import items as sanctified_and_sigil_items

if TYPE_CHECKING:
    from src.item.models import Item

from src.perception import parse_item_text

ALL_ITEMS = [*sanctified_and_sigil_items, *bloodied_items, *horadric_and_equipment_items]

SIGIL_TYPES = {ItemType.Sigil, ItemType.EscalationSigil}
items = [item for item in ALL_ITEMS if item[1].item_type in SIGIL_TYPES]


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_sigils(input_item: list[str], expected_item: Item):
    item = parse_item_text(input_item)
    assert item == expected_item
