from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING

import pywintypes
import win32file
import win32pipe

if TYPE_CHECKING:
    import logging
    import queue
    from collections.abc import Callable


def create_pipe(logger: logging.Logger):
    try:
        return win32pipe.CreateNamedPipe(
            r"\\.\pipe\d4lf",
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1,
            65536,
            65536,
            0,
            None,
        )
    except pywintypes.error as e:
        if e.args[0] == 231:  # ERROR_PIPE_BUSY
            logger.error("")
            logger.error("=" * 80)
            logger.error("D4LF IS ALREADY RUNNING")
            logger.error("=" * 80)
            logger.error("")
            logger.error("You already have D4LF running in another window.")
            logger.error("Please close your windows and re-launch.")
            logger.error("")
            logger.error("=" * 80)
            sys.exit(1)
        raise


def read_pipe(
    create_pipe_fn: Callable[[], object],
    data_queue: queue.Queue[str],
    logger: logging.Logger,
    set_connected: Callable[[bool], None],
) -> None:
    while True:
        handle = create_pipe_fn()
        logger.debug("Waiting for TTS client to connect")

        win32pipe.ConnectNamedPipe(handle, None)
        logger.info("TTS client connected")
        set_connected(True)

        while True:
            try:
                # Block until data is available (assumes PIPE_WAIT)
                win32file.ReadFile(handle, 0, None)
                # Query message size
                _, _, message_size = win32pipe.PeekNamedPipe(handle, 0)
                # Read message
                _, data = win32file.ReadFile(handle, message_size, None)
                data = data.decode().replace("\x00", "")
                if not data:
                    continue
                if "DISCONNECTED" in data:
                    break
                data_queue.put(data)
            except Exception:
                logger.exception("Error while reading data")

        win32file.CloseHandle(handle)
        logger.info("TTS client disconnected")
        set_connected(False)


def start_connection(
    start_find_item: Callable[[], None], start_read_pipe: Callable[[], None], logger: logging.Logger
) -> None:
    logger.info("Starting TTS listener. Hover over an item or button to perform the TTS connection.")
    threading.Thread(target=start_find_item, daemon=True).start()
    threading.Thread(target=start_read_pipe, daemon=True).start()
