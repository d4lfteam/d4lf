"""Thread-safe runtime state for the active Paragon overlay."""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.paragon.overlay.controller import ParagonOverlay

_CURRENT_OVERLAY: ParagonOverlay | None = None
_CLOSE_REQUESTED = threading.Event()
_OVERLAY_LOCK = threading.Lock()


def get_overlay() -> ParagonOverlay | None:
    """Return the currently composed overlay, if one exists."""
    with _OVERLAY_LOCK:
        return _CURRENT_OVERLAY


def set_overlay(overlay: ParagonOverlay) -> None:
    """Publish an overlay after its UI object has been constructed."""
    global _CURRENT_OVERLAY
    with _OVERLAY_LOCK:
        _CURRENT_OVERLAY = overlay
        _CLOSE_REQUESTED.clear()


def clear_overlay(overlay: ParagonOverlay | None = None) -> None:
    """Clear the current overlay, preserving a newer replacement if present."""
    global _CURRENT_OVERLAY
    with _OVERLAY_LOCK:
        if overlay is None or _CURRENT_OVERLAY is overlay:
            _CURRENT_OVERLAY = None


def close_requested() -> threading.Event:
    """Return the event used to request closure from a worker thread."""
    return _CLOSE_REQUESTED


def request_close() -> None:
    """Signal the active overlay's UI thread to close it."""
    _CLOSE_REQUESTED.set()
