import logging

from src.desktop import call_on_ui_thread, get_root
from src.overlay.statistics import StatsSnapshot, subscribe_stats, unsubscribe_stats
from src.overlay.widget.shared import BOSS_TIMER_SLOT
from src.overlay.widget.widget import BossTimerOverlay

LOGGER = logging.getLogger(__name__)


def _on_stats(snapshot: StatsSnapshot) -> None:
    """Compose the UI update at the lifecycle boundary."""
    update_stats(
        gph=snapshot.gph,
        total_gained=snapshot.total_gained,
        eph=snapshot.eph,
        total_exp=snapshot.total_exp,
        t2l=snapshot.t2l,
    )


def open_overlay() -> None:
    def create() -> None:
        with BOSS_TIMER_SLOT.lock:
            if BOSS_TIMER_SLOT.get() is None:
                overlay = BossTimerOverlay(get_root(), on_closed=_forget)
                BOSS_TIMER_SLOT.set(overlay)
                subscribe_stats(_on_stats)

    call_on_ui_thread(create)


def request_close() -> None:
    overlay = BOSS_TIMER_SLOT.get()
    if overlay is not None:

        def close(overlay: BossTimerOverlay = overlay) -> None:
            if overlay.winfo_exists():
                overlay.destroy()
            _forget(overlay)

        call_on_ui_thread(close)


def is_open() -> bool:
    return BOSS_TIMER_SLOT.is_open()


def _forget(overlay: BossTimerOverlay | None) -> None:
    if overlay is None or BOSS_TIMER_SLOT.get() is overlay:
        BOSS_TIMER_SLOT.clear(overlay)
        unsubscribe_stats(_on_stats)


def update_stats(
    *,
    gph: int | None = None,
    total_gained: int | None = None,
    eph: int | None = None,
    total_exp: int | None = None,
    t2l: str | None = None,
) -> None:
    overlay = BOSS_TIMER_SLOT.get()
    if overlay is not None:
        visible_overlay = overlay
        call_on_ui_thread(
            lambda: visible_overlay.update_stats(
                gph=gph, total_gained=total_gained, eph=eph, total_exp=total_exp, t2l=t2l
            )
        )
