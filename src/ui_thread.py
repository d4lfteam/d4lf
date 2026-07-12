"""Shared Tk UI thread. Every overlay subsystem attaches to this one root instead of creating its own tk.Tk()."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from collections.abc import Callable

LOGGER = logging.getLogger(__name__)

_UI_THREAD: threading.Thread | None = None
UiCallback = Callable[[], object]
_UI_QUEUE: queue.Queue[tuple[UiCallback, threading.Event | None, dict[str, object]]] = queue.Queue()
_UI_ROOT: tk.Tk | None = None
_UI_READY = threading.Event()
_START_LOCK = threading.Lock()


def _tk_thread_main() -> None:
    """Own the shared Tk root and execute queued UI work on that thread."""
    global _UI_ROOT
    # Create a hidden root window. Overlay subsystems attach Toplevels to this
    # root, but Tk still needs one interpreter that owns the event loop.
    root = tk.Tk()
    root.withdraw()
    _UI_ROOT = root
    _UI_READY.set()

    def _pump_queue() -> None:
        """Run all queued UI callbacks and reschedule the queue pump."""
        while True:
            try:
                fn, done, box = _UI_QUEUE.get_nowait()
            except queue.Empty:
                break

            try:
                box["result"] = fn()
            except Exception as exc:
                LOGGER.exception("Shared UI thread callback failed")
                box["error"] = exc
            finally:
                if done:
                    done.set()

        root.after(25, _pump_queue)

    root.after(0, _pump_queue)
    root.mainloop()


def ensure_ui_thread() -> None:
    """Start the shared Tk UI thread once and wait until it is ready."""
    global _UI_THREAD
    with _START_LOCK:
        if _UI_THREAD is None or not _UI_THREAD.is_alive():
            _UI_READY.clear()
            _UI_THREAD = threading.Thread(target=_tk_thread_main, name="d4lf-ui-thread", daemon=True)
            _UI_THREAD.start()
    if not _UI_READY.wait(timeout=5.0):
        msg = "Shared Tk UI thread failed to init"
        raise RuntimeError(msg)


def get_root() -> tk.Tk:
    """Return the shared root, starting the UI thread first if needed."""
    ensure_ui_thread()
    if _UI_ROOT is None:
        message = "Shared Tk UI root is unavailable"
        raise RuntimeError(message)
    return _UI_ROOT


def join_ui_thread() -> None:
    """Block the calling thread until the shared UI thread exits."""
    ensure_ui_thread()
    if _UI_THREAD is None:
        message = "Shared Tk UI thread is unavailable"
        raise RuntimeError(message)
    _UI_THREAD.join()


def call_on_ui_thread(fn: UiCallback) -> object:
    """Execute a callback on the Tk thread and wait for its return value."""
    ensure_ui_thread()
    done, box = threading.Event(), {}
    _UI_QUEUE.put((fn, done, box))
    done.wait()
    exc = box.get("error")
    if isinstance(exc, BaseException):
        raise exc
    return box.get("result")


def post_to_ui_thread(fn: UiCallback) -> None:
    """Queue work on the Tk thread without blocking the caller."""
    ensure_ui_thread()
    _UI_QUEUE.put((fn, None, {}))


def is_alive(w: tk.Misc | None, mapped: bool = False) -> bool:
    """Safely check if a widget exists (and optionally is mapped)."""
    try:
        return bool(w and w.winfo_exists() and (w.winfo_ismapped() if mapped else True))
    except tk.TclError:
        return False


def create_overlay_toplevel(parent: tk.Misc) -> tuple[tk.Toplevel, tk.Canvas]:
    """Create the fullscreen, click-through, transparent Toplevel+Canvas pair every overlay starts from."""
    root = tk.Toplevel(parent)
    root.overrideredirect(boolean=True)
    root.attributes("-topmost", 1)
    root.attributes("-transparentcolor", "white")
    root.attributes("-alpha", 1.0)
    canvas = tk.Canvas(root, bg="white", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    return root, canvas
