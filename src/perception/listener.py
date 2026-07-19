from __future__ import annotations

import enum
import logging
import queue
import re
import threading
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

from src.perception.backend.core import load_backend

CONNECTED = False
LAST_ITEM: list[str] = []
_DATA_QUEUE = queue.Queue(maxsize=100)
_backend = load_backend()
LOGGER = logging.getLogger(__name__)


class ItemIdentifiers(enum.Enum):
    COMPASS = "Compass"
    ESCALATION_SIGIL = "Escalation Sigil"
    NIGHTMARE_SIGIL = "Nightmare Sigil"
    TRIBUTE = "TRIBUTE OF"
    WHISPERING_KEY = "WHISPERING KEY"


def find_item_start(data: list[str]) -> int | None:
    ignored_words = ["COMPASS AFFIXES", "DUNGEON AFFIXES", "AFFIXES", "SELECT ALL"]
    for index, item in reversed(list(enumerate(data))):
        if any(ignored in item for ignored in ignored_words):
            continue
        if any(item.startswith(identifier.value) for identifier in ItemIdentifiers):
            return index
        if len(re.sub(r"[^A-Za-z]", "", item)) >= 3 and item.isupper():
            return index
    return None


def filter_data(data: str) -> bool:
    return "Champions who earn the favor of" in data


def fix_data(data: str) -> str:
    for token in ["&apos;", "&quot;", "[FAVORITED ITEM]. ", "ￂﾠ", "(Spiritborn Only)", "[MARKED AS JUNK]. "]:
        data = data.replace(token, "")
    return data.strip()


class Publisher:
    _instance: ClassVar[Publisher | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()
    _item_subscribers: set[Callable[..., None]]
    _info_subscribers: set[Callable[..., None]]
    _subscriber_lock: threading.Lock

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._item_subscribers = set()
                cls._instance._info_subscribers = set()
                cls._instance._subscriber_lock = threading.Lock()
        return cls._instance

    def find_item(self) -> None:
        local_cache = []
        while True:
            data = fix_data(_DATA_QUEUE.get())
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
            self.publish_item(LAST_ITEM)
            local_cache = []

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


def set_connected(value: bool) -> None:
    global CONNECTED
    CONNECTED = value


def create_pipe():
    return _backend.create_pipe(LOGGER)


def read_pipe() -> None:
    _backend.read_pipe(create_pipe, _DATA_QUEUE, LOGGER, set_connected)


def start_connection() -> None:
    _backend.start_connection(Publisher().find_item, read_pipe, LOGGER)
