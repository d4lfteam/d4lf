import json
from pathlib import Path

from src.config import BASE_DIR
from src.item.data.item_type import ITEM_TYPE_ALIASES, ItemType, is_weapon


def test_item_type_data_keys_are_declared() -> None:
    with Path(BASE_DIR / "assets/lang/enUS/item_types.json").open(encoding="utf-8") as file:
        item_types = json.load(file)

    known_item_types = set(ItemType.__members__) | set(ITEM_TYPE_ALIASES)
    missing_item_types = sorted(set(item_types) - known_item_types)

    assert missing_item_types == []


def test_hand_crossbow_is_weapon() -> None:
    assert is_weapon(ItemType.Crossbow)


def test_slot_specific_item_type_aliases_resolve_to_canonical_types() -> None:
    assert {
        "DaggerOffHand": ItemType.Dagger,
        "FocusBookOffHand": ItemType.Focus,
        "Mace2HDruid": ItemType.Mace2H,
        "ShieldHTH": ItemType.Shield,
        "StaffDruid": ItemType.Staff,
        "StaffSorcerer": ItemType.Staff,
    } == ITEM_TYPE_ALIASES
