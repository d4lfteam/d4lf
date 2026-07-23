from src import automation


def test_automation_facade_exposes_inventory_and_window_operations():
    assert {"Inventory", "ItemSlot", "WindowSpec", "move_pointer"} <= set(automation.__all__)
    assert automation.WindowSpec("Diablo IV.exe").process_name == "Diablo IV.exe"


def test_automation_facade_delegates_hotkeys(monkeypatch):
    sent = []
    monkeypatch.setattr("src.settings.send", sent.append)

    automation.send_hotkey("ctrl+f11")

    assert sent == ["ctrl+f11"]
