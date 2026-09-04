import logging
import sys
import threading
import tkinter as tk  # ruff:ignore[typing-only-standard-library-import] - preserve module attribute
from contextlib import suppress

from src.desktop import call_on_ui_thread, get_root, is_alive, post_to_ui_thread
from src.paragon.data import load_builds_from_path
from src.paragon.overlay import state as overlay_state
from src.paragon.overlay.core import OverlayCoreMixin
from src.paragon.overlay.grid import OverlayGridMixin
from src.paragon.overlay.grid_assets import OverlayGridMixin as OverlayGridAssetsMixin
from src.paragon.overlay.lifecycle import OverlayLifecycleMixin
from src.paragon.overlay.popup import OverlayPopupMixin
from src.paragon.overlay.popup_build import OverlayPopupBuildMixin
from src.paragon.overlay.popup_measure import OverlayPopupMixin as OverlayPopupMeasureMixin
from src.paragon.overlay.profiles import OverlayUIMixin as OverlayProfilesMixin
from src.paragon.overlay.ui import OverlayUIMixin

LOGGER = logging.getLogger(__name__)


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
        overlay_state.set_overlay(overlay)
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

        overlay_state.set_overlay(overlay)

    call_on_ui_thread(_open_overlay)
    # The caller owns a worker thread per overlay session and expects that thread
    # to stay alive until the overlay closes, so block here on the close signal.
    closed.wait()
    return None


def request_close(overlay: ParagonOverlay | None = None) -> None:
    """Request that the current overlay closes, even from another thread."""
    if not (t := overlay or overlay_state.get_overlay()):
        return
    overlay_state.request_close()
    with suppress(Exception):
        post_to_ui_thread(lambda: t.close() if is_alive(t) else None)


if __name__ == "__main__":
    run_paragon_overlay()
