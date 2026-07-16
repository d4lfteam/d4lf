import enum
import logging
import queue
import re
import sys
import threading

from src import tts_backend_noop


def _singleton(cls):
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


if sys.platform == "win32":
    from src import tts_backend_windows as _backend
else:
    _backend = tts_backend_noop

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


@_singleton
class Publisher:
    def __init__(self):
        self._item_subscribers = set()
        self._info_subscribers = set()
        self._subscriber_lock = threading.Lock()

    def find_item(self) -> None:
        local_cache = []
        while True:
            data = fix_data(_DATA_QUEUE.get())
            # Pass numerical stat lines directly to info subscribers (Gold/Exp)
            if "gold" in data.lower() or "experience" in data.lower():
                self.publish_info(data)

            local_cache.append(data)
            if filter_data(data) or not any(word in data.lower() for word in ["mouse button", "action button"]):
                continue
            start = find_item_start(local_cache)
            if start is None:
                continue
            global LAST_ITEM
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
            self._item_subscribers.discard(subscriber)

    def publish_info(self, data):
        with self._subscriber_lock:
            for subscriber in self._info_subscribers:
                subscriber(data)

    def subscribe_info(self, subscriber):
        with self._subscriber_lock:
            self._info_subscribers.add(subscriber)

    def unsubscribe_info(self, subscriber):
        with self._subscriber_lock:
            self._info_subscribers.discard(subscriber)


def _set_connected(value: bool) -> None:
    global CONNECTED
    CONNECTED = value


def create_pipe():
    return _backend.create_pipe(LOGGER)


def read_pipe() -> None:
    _backend.read_pipe(create_pipe, _DATA_QUEUE, LOGGER, _set_connected)


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
    _backend.start_connection(Publisher().find_item, read_pipe, LOGGER)
