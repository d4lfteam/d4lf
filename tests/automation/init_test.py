from src import automation


def test_automation_facade_exposes_inventory_and_window_operations() -> None:
    assert {"Inventory", "ItemSlot", "WindowSpec", "move_pointer"} <= set(automation.__all__)
    assert automation.WindowSpec("Diablo IV.exe").process_name == "Diablo IV.exe"
