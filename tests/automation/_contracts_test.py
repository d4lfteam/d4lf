from typing import get_protocol_members

from src.automation._contracts import Inventory, StashInventory


def test_inventory_contracts_are_runtime_protocols():
    assert {"open", "is_open", "get_item_slots", "hover_item"} <= get_protocol_members(Inventory)
    assert "switch_to_tab" in get_protocol_members(StashInventory)
