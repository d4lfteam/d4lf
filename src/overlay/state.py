"""Leaf, thread-safe state shared by the overlay lifecycle and renderer."""

import threading

_OVERLAY_INSTANCE: object | None = None
_OVERLAY_LOCK = threading.RLock()


def get_overlay() -> object | None:
    """Return the currently composed overlay, if one exists."""
    with _OVERLAY_LOCK:
        return _OVERLAY_INSTANCE


def set_overlay(overlay: object) -> None:
    """Publish an overlay after its UI object has been constructed."""
    global _OVERLAY_INSTANCE
    with _OVERLAY_LOCK:
        _OVERLAY_INSTANCE = overlay


def clear_overlay(overlay: object | None = None) -> None:
    """Clear the current overlay, preserving a newer replacement if present."""
    global _OVERLAY_INSTANCE
    with _OVERLAY_LOCK:
        if overlay is None or _OVERLAY_INSTANCE is overlay:
            _OVERLAY_INSTANCE = None


def is_open() -> bool:
    """Return whether an overlay has been composed."""
    return get_overlay() is not None
