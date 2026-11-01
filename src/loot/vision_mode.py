"""Template shared by all vision modes."""

import logging
import queue
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.desktop import call_on_ui_thread, create_overlay_toplevel, get_root
from src.perception import Publisher

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable

LOGGER = logging.getLogger(__name__)


class VisionMode[C](ABC):
    """Template for a vision mode: a Tk overlay that draws queued commands, fed by TTS item events while running."""

    def __init__(self, root: tk.Toplevel, canvas: tk.Canvas) -> None:
        self.root = root
        self.canvas = canvas
        self.is_running = False
        self._queue: queue.Queue[C] = queue.Queue()
        # Runs on the Tk loop once the subclass is fully constructed, so the draw loop never sees a half-built mode.
        canvas.after(0, self.draw_from_queue)

    def submit(self, command: C) -> None:
        self._queue.put(command)

    def draw_from_queue(self) -> None:
        try:
            self.draw(self._queue.get_nowait())
        except queue.Empty:
            pass
        except Exception:
            LOGGER.exception("Error while drawing vision mode overlay")
        finally:
            # Always reschedule, otherwise a single drawing error would stop the redraw loop for good.
            self.canvas.after(10, self.draw_from_queue)

    @abstractmethod
    def draw(self, command: C) -> None: ...

    @abstractmethod
    def on_tts(self, _: list[str], /) -> None: ...

    @abstractmethod
    def on_stop(self) -> None:
        """Clean up before unsubscribing from item events."""

    def start(self) -> None:
        LOGGER.info("Starting Vision Mode")
        Publisher().subscribe_item(self.on_tts)
        self.is_running = True

    def stop(self) -> None:
        LOGGER.info("Stopping Vision Mode")
        self.on_stop()
        Publisher().unsubscribe_item(self.on_tts)
        self.is_running = False

    def running(self) -> bool:
        return self.is_running


def create_on_ui_thread[M](create: Callable[[tk.Toplevel, tk.Canvas], M]) -> M:
    """Build the overlay window and the vision mode on the UI thread and let it start drawing."""
    modes: list[M] = []

    def _build_ui() -> None:
        root, canvas = create_overlay_toplevel(get_root())
        modes.append(create(root, canvas))

    # Widget creation and every subsequent Tk call must happen on the shared UI thread.
    call_on_ui_thread(_build_ui)
    return modes[0]
