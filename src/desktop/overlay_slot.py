"""Thread-safe holder for the single active instance of an overlay."""

import threading


class OverlaySlot[T]:
    """Publish, look up, and clear the active overlay of one kind."""

    def __init__(self) -> None:
        self._overlay: T | None = None
        self._lock = threading.RLock()
        self._close_requested = threading.Event()

    @property
    def lock(self) -> threading.RLock:
        """Return the lock guarding the slot, for check-then-set sequences."""
        return self._lock

    @property
    def close_requested(self) -> threading.Event:
        """Return the event used to request closure from a worker thread."""
        return self._close_requested

    def get(self) -> T | None:
        """Return the currently published overlay, if one exists."""
        with self._lock:
            return self._overlay

    def set(self, overlay: T) -> None:
        """Publish an overlay after its UI object has been constructed."""
        with self._lock:
            self._overlay = overlay
            self._close_requested.clear()

    def clear(self, overlay: T | None = None) -> None:
        """Clear the slot, preserving a newer replacement if one was published."""
        with self._lock:
            if overlay is None or self._overlay is overlay:
                self._overlay = None

    def is_open(self) -> bool:
        """Return whether an overlay has been published."""
        return self.get() is not None

    def request_close(self) -> None:
        """Signal the active overlay's UI thread to close it."""
        self._close_requested.set()
