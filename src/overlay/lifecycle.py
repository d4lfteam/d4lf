import logging

from src.desktop import call_on_ui_thread, get_root
from src.overlay import state as _state
from src.overlay.settings import InfoSettingValue, load_settings
from src.overlay.statistics import StatsSnapshot, subscribe_stats, unsubscribe_stats
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
        with _state._OVERLAY_LOCK:
            if _state.get_overlay() is None:
                overlay = BossTimerOverlay(get_root(), on_closed=_forget)
                _state.set_overlay(overlay)
                subscribe_stats(_on_stats)

    call_on_ui_thread(create)


def request_close() -> None:
    overlay = _state.get_overlay()
    if overlay is not None:

        def close(overlay: BossTimerOverlay = overlay) -> None:
            if overlay.winfo_exists():
                overlay.destroy()
            _forget(overlay)

        call_on_ui_thread(close)


def is_open() -> bool:
    return _state.is_open()


def _forget(overlay: BossTimerOverlay | None) -> None:
    if overlay is None or _state.get_overlay() is overlay:
        _state.clear_overlay(overlay)
        unsubscribe_stats(_on_stats)


def update_stats(
    *,
    gph: int | None = None,
    total_gained: int | None = None,
    eph: int | None = None,
    total_exp: int | None = None,
    t2l: str | None = None,
) -> None:
    overlay = _state.get_overlay()
    if overlay is not None:
        visible_overlay = overlay
        call_on_ui_thread(
            lambda: visible_overlay.update_stats(
                gph=gph, total_gained=total_gained, eph=eph, total_exp=total_exp, t2l=t2l
            )
        )


def get_setting(key: str, default: InfoSettingValue = None) -> InfoSettingValue:
    return load_settings().get(key, default)
