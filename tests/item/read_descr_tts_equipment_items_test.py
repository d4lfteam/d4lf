import platform
from typing import TYPE_CHECKING

import pytest

from src.item.data.item_type import ItemType
from tests.item.read_descr_tts_cases_bloodied_items import items as bloodied_items
from tests.item.read_descr_tts_cases_horadric_and_equipment import items as horadric_and_equipment_items
from tests.item.read_descr_tts_cases_mythic_items import items as mythic_items
from tests.item.read_descr_tts_cases_sanctified_and_sigils import items as sanctified_and_sigil_items
from tests.item.read_descr_tts_cases_unique_gloves import items as unique_items

if TYPE_CHECKING:
    from src.item.models import Item

if platform.system() == "Windows":
    import src.tts
    from src.item.descr.read_descr_tts import read_descr

ALL_ITEMS = [*mythic_items, *unique_items, *sanctified_and_sigil_items, *bloodied_items, *horadric_and_equipment_items]

NON_EQUIPMENT_TYPES = {ItemType.Sigil, ItemType.EscalationSigil, ItemType.HoradricSeal, ItemType.Charm}
items = [item for item in ALL_ITEMS if item[1].item_type not in NON_EQUIPMENT_TYPES]
pytestmark = pytest.mark.skipif(platform.system() != "Windows", reason="Requires Windows TTS modules")


@pytest.mark.parametrize(("input_item", "expected_item"), items)
def test_equipment_items(input_item: list[str], expected_item: Item):
    src.tts.LAST_ITEM = input_item
    item = read_descr()
    assert item == expected_item
