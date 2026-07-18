from ._data import *
from ._overlaycore import OverlayCoreMixin
from ._overlaygrid import OverlayGridMixin
from ._overlaygridassets import OverlayGridMixin as OverlayGridAssetsMixin
from ._overlaylifecycle import OverlayLifecycleMixin
from ._overlaypopup import OverlayPopupMixin
from ._overlaypopupbuild import OverlayPopupBuildMixin
from ._overlaypopupmeasure import OverlayPopupMixin as OverlayPopupMeasureMixin
from ._overlayprofiles import OverlayUIMixin as OverlayProfilesMixin
from ._overlayui import OverlayUIMixin


class ParagonOverlay(
    OverlayCoreMixin,
    OverlayUIMixin,
    OverlayProfilesMixin,
    OverlayPopupMixin,
    OverlayPopupMeasureMixin,
    OverlayPopupBuildMixin,
    OverlayGridMixin,
    OverlayGridAssetsMixin,
    OverlayLifecycleMixin,
):
    """Tkinter Paragon overlay assembled from private behavior mixins."""


def run_paragon_overlay(preset_path: str | None = None, *, parent: tk.Misc | None = None) -> ParagonOverlay | None:
    """Open the overlay either on an existing Tk parent or on the shared UI thread."""
    try:
        if not (builds := load_builds_from_path(preset_path or (sys.argv[1] if len(sys.argv) > 1 else None))):
            LOGGER.warning("No Paragon data found in loaded profiles.")
            return None
    except Exception:
        LOGGER.exception("Failed to load Paragon preset")
        return None

    if parent is not None:
        # Embedding mode is used when another Tk application already owns the
        # event loop and can host the overlay directly.
        overlay = ParagonOverlay(parent, builds, on_close=None)
        with _OVERLAY_LOCK:
            global _CURRENT_OVERLAY
            _CURRENT_OVERLAY = overlay
            _CLOSE_REQUESTED.clear()
        return overlay

    closed = threading.Event()

    def _open_overlay() -> None:
        # NOTE: This runs on the shared Tk UI thread.
        try:
            overlay = ParagonOverlay(get_root(), builds, on_close=closed.set)
        except Exception:
            LOGGER.exception("Paragon overlay: failed to open")
            closed.set()
            return

        with _OVERLAY_LOCK:
            global _CURRENT_OVERLAY
            _CURRENT_OVERLAY = overlay
            _CLOSE_REQUESTED.clear()

    call_on_ui_thread(_open_overlay)
    # The caller owns a worker thread per overlay session and expects that thread
    # to stay alive until the overlay closes, so block here on the close signal.
    closed.wait()
    return None


def request_close(overlay: ParagonOverlay | None = None) -> None:
    """Request that the current overlay closes, even from another thread."""
    with _OVERLAY_LOCK:
        if not (t := overlay or _CURRENT_OVERLAY):
            return
        _CLOSE_REQUESTED.set()
    with suppress(Exception):
        post_to_ui_thread(lambda: t.close() if is_alive(t) else None)


if __name__ == "__main__":
    run_paragon_overlay()
