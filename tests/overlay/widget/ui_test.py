from typing import TYPE_CHECKING

from src.overlay.widget.widget import BossTimerOverlay

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


class _Packable:
    pack_calls: list[dict[str, JsonValue]]

    def __init__(self) -> None:
        self.pack_calls = []

    def pack(self, **kwargs: JsonValue) -> None:
        self.pack_calls.append(kwargs)

    def pack_forget(self) -> None:
        pass


def test_repack_shows_only_enabled_timer_groups(monkeypatch) -> None:
    overlay = object.__new__(BossTimerOverlay)
    overlay.orientation = "horizontal"
    overlay.show_wb = True
    overlay.show_legion = False
    overlay.show_ht = False
    overlay.show_gold = True
    overlay.show_gph = True
    overlay.show_total_gold = True
    overlay.show_exp = True
    overlay.show_eph = True
    overlay.show_total_exp = True
    overlay.show_t2l = True
    overlay.show_next_scan = True
    overlay.capture_gold_stats = False
    overlay.capture_exp_stats = False
    overlay._gold_initialized = False
    overlay._exp_initialized = False
    groups = {
        name: _Packable() for name in ("wb_group", "legion_group", "ht_group", "stats_group", "exp_group", "t2l_group")
    }
    for name, group in groups.items():
        monkeypatch.setattr(BossTimerOverlay, name, group, raising=False)

    overlay._repack()

    assert groups["wb_group"].pack_calls == [{"side": "left", "padx": 2}]
    assert groups["legion_group"].pack_calls == []
    assert groups["ht_group"].pack_calls == []
