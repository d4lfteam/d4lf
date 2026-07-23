from src.loot import orchestration as _orchestration
from src.settings import ItemRefreshType


def test_loot_filter_processes_stash_tabs_before_inventory(monkeypatch):
    calls = []

    class Settings:
        class General:
            check_chest_tabs = [2, 4]

        general = General()

    class Stash:
        def is_open(self):
            return True

        def switch_to_tab(self, tab):
            calls.append(("tab", tab))

    class Inventory:
        def open(self):
            raise AssertionError

    monkeypatch.setattr(_orchestration, "get_settings", lambda: Settings())
    monkeypatch.setattr(_orchestration, "stash_inventory", lambda: Stash())
    monkeypatch.setattr(_orchestration, "character_inventory", lambda: Inventory())
    monkeypatch.setattr(_orchestration, "move_pointer", lambda *pos: calls.append(("pointer", pos)))
    monkeypatch.setattr(_orchestration, "abs_window_to_monitor", lambda pos: pos)
    monkeypatch.setattr(_orchestration, "check_items", lambda *args, **kwargs: calls.append(("check", args, kwargs)))
    _orchestration.run_loot_filter(ItemRefreshType.no_refresh)
    assert [call[0:2] for call in calls if call[0] == "tab"] == [("tab", 2), ("tab", 4)]
    assert [call[0] for call in calls].count("check") == 3
