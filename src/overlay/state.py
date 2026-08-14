"""Leaf, thread-safe state shared by the overlay lifecycle and renderer."""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.overlay.widget.widget import BossTimerOverlay

_OVERLAY_INSTANCE: BossTimerOverlay | None = None
_OVERLAY_LOCK = threading.RLock()


def get_overlay() -> BossTimerOverlay | None:
    """Return the currently composed overlay, if one exists."""
    with _OVERLAY_LOCK:
        return _OVERLAY_INSTANCE


def set_overlay(overlay: BossTimerOverlay) -> None:
    """Publish an overlay after its UI object has been constructed."""
    global _OVERLAY_INSTANCE
    with _OVERLAY_LOCK:
        _OVERLAY_INSTANCE = overlay


def clear_overlay(overlay: BossTimerOverlay | None = None) -> None:
    """Clear the current overlay, preserving a newer replacement if present."""
    global _OVERLAY_INSTANCE
    with _OVERLAY_LOCK:
        if overlay is None or _OVERLAY_INSTANCE is overlay:
            _OVERLAY_INSTANCE = None


def is_open() -> bool:
    """Return whether an overlay has been composed."""
    return get_overlay() is not None
