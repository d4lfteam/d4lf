from dataclasses import dataclass
import enum
import logging
import queue
import re
import sys
import threading

import pywintypes
import win32file
import win32pipe

from src.config.loader import IniConfigLoader
from src.config.helper import singleton

CONNECTED = False
LAST_ITEM = []
TO_FILTER = ["Champions who earn the favor of"]
_DATA_QUEUE = queue.Queue(maxsize=100)

LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class InfoStat:
    name: str
    value: int
    max_value: int | None = None


class ItemIdentifiers(enum.Enum):
    COMPASS = "Compass"
    ESCALATION_SIGIL = "Escalation Sigil"
    NIGHTMARE_SIGIL = "Nightmare Sigil"
    TRIBUTE = "TRIBUTE OF"
    WHISPERING_KEY = "WHISPERING KEY"


@singleton
class Publisher:
    def __init__(self):
        self._item_subscribers = set()
        self._info_subscribers = set()
        self._subscriber_lock = threading.Lock()

    def find_item(self) -> None:
        global LAST_ITEM
        local_cache = []
        while True:
            data = fix_data(_DATA_QUEUE.get())
            local_cache.append(data)

            # Debug logging for potential stat readouts
            if any(word in data.lower() for word in ["gold", "experience", "currency"]):
                from src.info_overlay import get_info_setting
                if get_info_setting("debug_tts", False):
                    LOGGER.info(f"TTS Raw Stat String: '{data}'")

            if filter_data(data):
                continue

            is_stat = any(word in data.lower() for word in ["gold", "experience"])
            is_item_end = any(word in data.lower() for word in ["mouse button", "action button"])

            if is_stat:
                stat = _parse_stat(data)
                if stat:
                    self.publish_info(stat)
            elif is_item_end:
                start = find_item_start(local_cache)
                if start is not None:
                    LAST_ITEM = local_cache[start:]
                    LOGGER.debug(f"TTS Found: {LAST_ITEM}")
                    local_cache = []
                    self.publish_item(LAST_ITEM)

    def publish_item(self, data):
        with self._subscriber_lock:
            for subscriber in self._item_subscribers:
                subscriber(data)

    def subscribe_item(self, subscriber):
        with self._subscriber_lock:
            self._item_subscribers.add(subscriber)

    def unsubscribe_item(self, subscriber):
        with self._subscriber_lock:
            self._item_subscribers.remove(subscriber)

    def publish_info(self, data: InfoStat):
        with self._subscriber_lock:
            for subscriber in self._info_subscribers:
                subscriber(data)

    def subscribe_info(self, subscriber):
        with self._subscriber_lock:
            self._info_subscribers.add(subscriber)

    def unsubscribe_info(self, subscriber):
        with self._subscriber_lock:
            self._info_subscribers.remove(subscriber)


def _parse_stat(raw_line: str) -> InfoStat | None:
    # Handle Gold statistics from raw TTS string (e.g., '2,225,130,802 Gold')
    if (
        "gold" in raw_line.lower()
        and not any(x in raw_line.lower() for x in ["sell value", "repair", "cost", "price", "buy", "fee", "spent", "purchase"])
        and (match := re.search(r"([0-9,.]+)\s+Gold", raw_line, re.IGNORECASE))
    ):
        raw_val = re.sub(r"\D", "", match.group(1))
        if raw_val:
            return InfoStat(name="gold_balance", value=int(raw_val))
    # Handle Experience statistics (e.g., 'Level 209 Experience: 55,843,725 / 74,304,757')
    elif "experience" in raw_line.lower() and (match := re.search(r"Experience:\s+([0-9,.]+)\s+/\s+([0-9,.]+)", raw_line, re.IGNORECASE)):
        raw_val = re.sub(r"\D", "", match.group(1))
        raw_mx = re.sub(r"\D", "", match.group(2))
        if raw_val and raw_mx:
            return InfoStat(name="experience_gain", value=int(raw_val), max_value=int(raw_mx))
    return None


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
    except pywintypes.error as e:
        if e.args[0] == 231:  # ERROR_PIPE_BUSY
            LOGGER.error("")
            LOGGER.error("=" * 80)
            LOGGER.error("D4LF IS ALREADY RUNNING")
            LOGGER.error("=" * 80)
            LOGGER.error("")
            LOGGER.error("You already have D4LF running in another window.")
            LOGGER.error("Please close your windows and re-launch.")
            LOGGER.error("")
            LOGGER.error("=" * 80)

            sys.exit(1)
        else:
            raise  # Re-raise other errors


def read_pipe() -> None:
    while True:
        handle = create_pipe()
        LOGGER.debug("Waiting for TTS client to connect")

        win32pipe.ConnectNamedPipe(handle, None)
        LOGGER.info("TTS client connected")
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
        LOGGER.info("TTS client disconnected")
        CONNECTED = False


def find_item_start(data: list[str]) -> int | None:
    ignored_words = ["COMPASS AFFIXES", "DUNGEON AFFIXES", "AFFIXES", "SELECT ALL"]

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
    LOGGER.info("Starting TTS listener. Hover over an item or button to perform the TTS connection.")
    threading.Thread(target=Publisher().find_item, daemon=True).start()
    threading.Thread(target=read_pipe, daemon=True).start()
