from __future__ import annotations

from typing import TYPE_CHECKING

from src.dataloader import Dataloader
from src.item.data.item_type import ItemType, is_consumable
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.models import Item
from src.scripts import correct_name
from src.tts import ItemIdentifiers

if TYPE_CHECKING:
    from collections.abc import Callable


def update_item_object(item: Item, rarity=None, item_type=None) -> Item:
    if rarity:
        item.rarity = rarity
    if item_type:
        item.item_type = item_type

    return item


def get_item_rarity(data: str) -> ItemRarity | None:
    return next((rar for rar in ItemRarity if rar.value == data.lower()), ItemRarity.Common)


def get_item_type(data: str):
    return next((it for it in ItemType if it.value == data.lower()), None)


def create_base_item_from_tts(
    tts_item: list[str],
    *,
    dataloader=None,
    correct_name_func: Callable[[str], str | None] = correct_name,
) -> Item | None:
    item = Item(original_name=tts_item[0])
    if tts_item[1].endswith(ItemIdentifiers.COMPASS.value):
        return update_item_object(item, rarity=ItemRarity.Common, item_type=ItemType.Compass)

    if ItemIdentifiers.NIGHTMARE_SIGIL.value.upper() in tts_item[0].upper():
        if "Nightmare Sigil is used" in tts_item[0]:
            return None
        if "bloodied" in tts_item[1].lower():
            item.seasonal_attribute = SeasonalAttribute.bloodied
        return update_item_object(item, rarity=ItemRarity.Common, item_type=ItemType.Sigil)

    if tts_item[0].startswith(ItemIdentifiers.ESCALATION_SIGIL.value):
        return update_item_object(item, rarity=ItemRarity.Common, item_type=ItemType.EscalationSigil)

    if ItemIdentifiers.TRIBUTE.value in tts_item[0]:
        item.item_type = ItemType.Tribute
        search_string_split = tts_item[1].split(" ")
        item.rarity = get_item_rarity(search_string_split[0])
        item.name = correct_name_func(" ".join(search_string_split[1:]))
        return item

    if tts_item[0].startswith(ItemIdentifiers.WHISPERING_KEY.value):
        return update_item_object(item, item_type=ItemType.Consumable)

    if tts_item[1].lower().endswith("summoning"):
        return update_item_object(item, item_type=ItemType.Material)

    if tts_item[1].lower().endswith("gem"):
        return update_item_object(item, item_type=ItemType.Gem)

    if tts_item[1].lower().endswith("whispering wood"):
        return update_item_object(item, item_type=ItemType.WhisperingWood)

    if tts_item[1].lower().startswith("cosmetic"):
        return update_item_object(item, item_type=ItemType.Cosmetic)

    if tts_item[1].lower().endswith("boss key"):
        return update_item_object(item, item_type=ItemType.LairBossKey)

    if "rune of" in tts_item[1].lower():
        item.item_type = ItemType.Rune
        search_string_split = tts_item[1].lower().split(" rune of ")
        item.rarity = get_item_rarity(search_string_split[0])
        return item

    if any("Cost : " in value or "Cost:" in value for value in tts_item):
        item.is_in_shop = True

    if tts_item[1].lower().endswith("cache"):
        item.item_type = ItemType.Cache
        return item

    if tts_item[1].lower().endswith("elixir"):
        item.item_type = ItemType.Elixir
    elif tts_item[1].lower().endswith("incense"):
        item.item_type = ItemType.Incense
    elif "temper manual" in tts_item[1].lower():
        item.item_type = ItemType.TemperManual
    elif any(tts_item[1].lower().endswith(x) for x in ["consumable", "scroll"]):
        item.item_type = ItemType.Consumable

    if is_consumable(item.item_type):
        search_string_split = tts_item[1].split(" ")
        item.rarity = get_item_rarity(search_string_split[0])
        return item

    if "bloodied" in tts_item[1].lower():
        item.seasonal_attribute = SeasonalAttribute.bloodied

    if any("sanctified" in tts_item[i].lower() for i in range(3, min(7, len(tts_item)))):
        item.seasonal_attribute = SeasonalAttribute.sanctified

    search_string = tts_item[1].lower().replace("ancestral", "").replace("bloodied", "").strip()
    search_string_split = search_string.split(" ")
    item.rarity = get_item_rarity(search_string_split[0])
    starting_item_type_index = 1
    if item.rarity == ItemRarity.Mythic:
        starting_item_type_index = 2
    elif item.rarity == ItemRarity.Common:
        starting_item_type_index = 0
    item.item_type = get_item_type(" ".join(search_string_split[starting_item_type_index:]))
    item.name = correct_name_func(tts_item[0])
    if dataloader is None:
        dataloader = Dataloader()
    if item.name in dataloader.bad_tts_uniques:
        item.name = dataloader.bad_tts_uniques[item.name]
    for line in tts_item:
        if "item power" in line.lower():
            from src.item.descr.text import find_number

            item.power = int(find_number(line))
            break
    return item
