import logging
import threading

from src.desktop import call_on_ui_thread, get_root

from . import _widget_shared
from ._settings import InfoSettingValue, load_settings
from ._widget import BossTimerOverlay

LOGGER = logging.getLogger(__name__)
_lock = threading.RLock()


def open_overlay() -> None:
    def create() -> None:
        with _lock:
            if _widget_shared._OVERLAY_INSTANCE is None:
                _widget_shared._OVERLAY_INSTANCE = BossTimerOverlay(get_root())

    call_on_ui_thread(create)


def request_close() -> None:
    with _lock:
        overlay = _widget_shared._OVERLAY_INSTANCE
    if overlay is not None:

        def close() -> None:
            if overlay.winfo_exists():
                overlay.destroy()
            _forget(overlay)

        call_on_ui_thread(close)


def is_open() -> bool:
    with _lock:
        return _widget_shared._OVERLAY_INSTANCE is not None


def _forget(overlay: object | None) -> None:
    with _lock:
        if _widget_shared._OVERLAY_INSTANCE is overlay:
            _widget_shared._OVERLAY_INSTANCE = None


def update_stats(
    *,
    gph: int | None = None,
    total_gained: int | None = None,
    eph: int | None = None,
    total_exp: int | None = None,
    t2l: str | None = None,
) -> None:
    with _lock:
        overlay = _widget_shared._OVERLAY_INSTANCE
    if overlay is not None:
        call_on_ui_thread(
            lambda: overlay.update_stats(gph=gph, total_gained=total_gained, eph=eph, total_exp=total_exp, t2l=t2l)
        )


def get_setting(key: str, default: object = None) -> InfoSettingValue | object:
    return load_settings().get(key, default)
