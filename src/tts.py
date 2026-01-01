import enum
import logging
import queue
import re
import sys
import threading

import pywintypes
import win32file
import win32pipe

from src.config.helper import singleton

CONNECTED = False
LAST_ITEM = []
TO_FILTER = ["Champions who earn the favor of"]
_DATA_QUEUE = queue.Queue(maxsize=100)

LOGGER = logging.getLogger(__name__)


class ItemIdentifiers(enum.Enum):
    COMPASS = "Compass"
    ESCALATION_SIGIL = "Escalation Sigil"
    NIGHTMARE_SIGIL = "Nightmare Sigil"
    TRIBUTE = "TRIBUTE OF"
    WHISPERING_KEY = "WHISPERING KEY"


@singleton
class Publisher:
    def __init__(self):
        self._subscribers = set()

    def find_item(self) -> None:
        local_cache = []
        while True:
            data = fix_data(_DATA_QUEUE.get())
            local_cache.append(data)
            if not filter_data(data) and (
                any(word in data.lower() for word in ["mouse button", "action button"])
                and (start := find_item_start(local_cache)) is not None
            ):
                global LAST_ITEM
                LAST_ITEM = local_cache[start:]
                LOGGER.debug(f"TTS Found: {LAST_ITEM}")
                local_cache = []
                self.publish(LAST_ITEM)

    def publish(self, data):
        for subscriber in self._subscribers:
            subscriber(data)

    def subscribe(self, subscriber):
        self._subscribers.add(subscriber)

    def unsubscribe(self, subscriber):
        self._subscribers.remove(subscriber)


def create_pipe():
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
    except pywintypes.error as e:  # ← Move this LEFT (same level as try)
        if e.args[0] == 231:  # ERROR_PIPE_BUSY
            LOGGER.error("[CLEAN]")
            LOGGER.error("[CLEAN]" + "=" * 80)
            LOGGER.error("[CLEAN]" + "D4LF IS ALREADY RUNNING")
            LOGGER.error("[CLEAN]" + "=" * 80)
            LOGGER.error("[CLEAN]")
            LOGGER.error("[CLEAN]" + "You already have D4LF running in another window.")
            LOGGER.error("[CLEAN]" + "Please close your windows and re-launch.")
            LOGGER.error("[CLEAN]")
            LOGGER.error("[CLEAN]" + "=" * 80)

            sys.exit(1)
        else:
            raise  # Re-raise other errors


def read_pipe() -> None:
    while True:
        handle = create_pipe()
        LOGGER.debug("Waiting for TTS client to connect")

        win32pipe.ConnectNamedPipe(handle, None)
        LOGGER.debug("TTS client connected")
        global CONNECTED
        CONNECTED = True

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
                _DATA_QUEUE.put(data)
            except Exception:
                LOGGER.exception("Error while reading data")

        win32file.CloseHandle(handle)
        LOGGER.debug("TTS client disconnected")
        CONNECTED = False


def find_item_start(data: list[str]) -> int | None:
    ignored_words = ["COMPASS AFFIXES", "DUNGEON AFFIXES", "AFFIXES"]

    for index, item in reversed(list(enumerate(data))):
        if any(ignored in item for ignored in ignored_words):
            continue

        if any(item.startswith(x) for x in [y.value for y in ItemIdentifiers]):
            return index

        cleaned_str = re.sub(r"[^A-Za-z]", "", item)
        if len(cleaned_str) >= 3 and item.isupper():
            return index

    return None


def filter_data(data: str) -> bool:
    return any(word in data for word in TO_FILTER)


def fix_data(data: str) -> str:
    to_remove = ["&apos;", "&quot;", "[FAVORITED ITEM]. ", "ￂﾠ", "(Spiritborn Only)", "[MARKED AS JUNK]. "]

    for item in to_remove:
        data = data.replace(item, "")

    return data.strip()


def start_connection() -> None:
    LOGGER.info("Starting tts listener")
    threading.Thread(target=Publisher().find_item, daemon=True).start()
    threading.Thread(target=read_pipe, daemon=True).start()