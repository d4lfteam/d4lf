import logging
import re
import time

from src.perception import Publisher

from ._settings import load_settings, save_settings
from ._singleton import singleton

LOGGER = logging.getLogger(__name__)


def _notify(
    *,
    gph: int | None = None,
    total_gained: int | None = None,
    eph: int | None = None,
    total_exp: int | None = None,
    t2l: str | None = None,
) -> None:
    # ruff:ignore[import-outside-top-level] - breaks the lifecycle/statistics import cycle
    from ._lifecycle import update_stats

    update_stats(gph=gph, total_gained=total_gained, eph=eph, total_exp=total_exp, t2l=t2l)


class _SessionStats:
    def __init__(self):
        self.start_time: float | None = None
        persisted = load_settings()
        persisted_gold = persisted.get("session_total_gold", 0)
        persisted_exp = persisted.get("session_total_exp", 0)
        self.total_gold: int = persisted_gold if isinstance(persisted_gold, int) else 0
        self.total_exp: int = persisted_exp if isinstance(persisted_exp, int) else 0
        self.pending_gold: int | None = None
        self.gold_verify_count = 0
        self.last_gold: int | None = None
        self.last_exp: int | None = None
        self.max_exp: int | None = None
        self._subscribed = False

    def subscribe(self) -> None:
        if not self._subscribed:
            Publisher().subscribe_info(self.on_info_stat)
            self._subscribed = True

    def unsubscribe(self) -> None:
        if self._subscribed:
            Publisher().unsubscribe_info(self.on_info_stat)
            self._subscribed = False

    def reset_gold(self) -> None:
        self.total_gold = 0
        self.pending_gold = None
        self.gold_verify_count = 0
        self.last_gold = None
        self._persist()
        _notify(gph=0, total_gained=0)

    def reset_exp(self) -> None:
        self.total_exp = 0
        self.last_exp = None
        self.max_exp = None
        self._persist()
        _notify(eph=0, total_exp=0, t2l="-")

    def _persist(self) -> None:
        save_settings({"session_total_gold": self.total_gold, "session_total_exp": self.total_exp})

    def _rate(self, total: int) -> int:
        if self.start_time is None:
            self.start_time = time.time()
        elapsed = (time.time() - self.start_time) / 3600
        return int(total / elapsed) if elapsed > 1 / 60 else 0

    def on_info_stat(self, raw_line: str) -> None:
        config = load_settings()
        text = raw_line.lower()
        if not config.get("capture_gold_stats") and not config.get("capture_exp_stats"):
            return
        if "gold" in text and not any(
            word in text for word in ("sell value", "repair", "cost", "price", "buy", "fee", "spent", "purchase")
        ):
            match = re.search(r"([0-9,.]+)\s+Gold", raw_line, re.IGNORECASE)
            if not match or not config.get("capture_gold_stats"):
                return
            value = int(re.sub(r"\D", "", match.group(1)))
            if self.last_gold is None:
                self.last_gold = value
                self.start_time = self.start_time or time.time()
                _notify(total_gained=self.total_gold)
                return
            if value == self.last_gold:
                self.pending_gold = None
                self.gold_verify_count = 0
                return
            self.gold_verify_count = (
                self.gold_verify_count + 1 if self.pending_gold is not None and value >= self.pending_gold else 1
            )
            self.pending_gold = value
            if self.gold_verify_count >= 3:
                if not (self.last_gold > 0 and value > self.last_gold * 10 and value > 10_000_000) and not (
                    value < self.last_gold * 0.01 and self.last_gold > 10_000_000
                ):
                    self.total_gold += max(0, value - self.last_gold)
                self.last_gold = value
                self.pending_gold = None
                self.gold_verify_count = 0
                self._persist()
                _notify(gph=self._rate(self.total_gold), total_gained=self.total_gold)
            return
        match = re.search(r"Experience:\s+([0-9,.]+)\s+/\s+([0-9,.]+)", raw_line, re.IGNORECASE)
        if "experience" not in text or not match or not config.get("capture_exp_stats"):
            return
        value, maximum = (int(re.sub(r"\D", "", part)) for part in match.groups())
        if self.last_exp is None:
            self.last_exp, self.max_exp = value, maximum
            self.start_time = self.start_time or time.time()
            _notify(total_exp=self.total_exp, t2l="-")
            return
        self.total_exp += max(0, value - self.last_exp)
        self.last_exp, self.max_exp = value, maximum or self.max_exp
        eph = self._rate(self.total_exp)
        t2l = "-"
        if eph and self.max_exp:
            hours = max(0, self.max_exp - value) / eph
            t2l = f"{int(hours * 60)}m" if hours < 1 else f"{int(hours)}h {int(hours % 1 * 60)}m"
        self._persist()
        _notify(eph=eph, total_exp=self.total_exp, t2l=t2l)


SessionStats = singleton(_SessionStats)
