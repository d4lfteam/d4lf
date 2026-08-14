import time

from src.overlay import InventoryExpTracker


def test_inventory_tracker_cooldown_survives_new_facade_instance() -> None:
    first = InventoryExpTracker()
    first.last_hover_time = time.time()
    second = InventoryExpTracker()
    assert second is first
    assert second.last_hover_time == first.last_hover_time
