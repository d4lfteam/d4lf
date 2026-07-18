from src.automation._inventory import ItemSlot


def test_item_slot_defaults_are_unmarked():
    slot = ItemSlot((1, 2, 3, 4), (2, 4))
    assert not slot.is_fav
    assert not slot.is_junk
