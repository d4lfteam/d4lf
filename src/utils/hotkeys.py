import threading
from collections import defaultdict
from typing import TYPE_CHECKING

from pynput import keyboard

if TYPE_CHECKING:
    from collections.abc import Callable

_VALID_KEY_NAMES = {name for name in dir(keyboard.Key) if not name.startswith("_")}

_CONTROLLER = keyboard.Controller()


def _split_hotkey_tokens(hotkey: str) -> list[str]:
    return [token.strip().lower() for token in hotkey.split("+") if token.strip()]


def _normalize_token(token: str) -> str:
    raw_token = token.strip().lower()
    if not raw_token:
        msg = "Hotkey cannot be empty."
        raise ValueError(msg)

    is_bracketed = raw_token.startswith("<") or raw_token.endswith(">")
    if is_bracketed and not (raw_token.startswith("<") and raw_token.endswith(">")):
        msg = f"Key '{raw_token}' is not mapped to any known key."
        raise ValueError(msg)

    key_name = raw_token[1:-1].strip() if raw_token.startswith("<") and raw_token.endswith(">") else raw_token
    if len(key_name) == 1 and not is_bracketed:
        return key_name
    if key_name in _VALID_KEY_NAMES:
        return f"<{key_name}>"

    msg = f"Key '{key_name}' is not mapped to any known key."
    raise ValueError(msg)


def normalize_hotkey(hotkey: str) -> str:
    tokens = _split_hotkey_tokens(hotkey)
    if not tokens:
        msg = "Hotkey cannot be empty."
        raise ValueError(msg)

    return "+".join(_normalize_token(token) for token in tokens)


def validate_hotkey(hotkey: str) -> str:
    keyboard.HotKey.parse(normalize_hotkey(hotkey))
    return hotkey


def _to_pressable(token: str):
    normalized = _normalize_token(token)
    if normalized.startswith("<") and normalized.endswith(">"):
        return getattr(keyboard.Key, normalized[1:-1])
    return normalized


def press(key: str) -> None:
    _CONTROLLER.press(_to_pressable(key))


def release(key: str) -> None:
    _CONTROLLER.release(_to_pressable(key))


def send(hotkey: str) -> None:
    keys = [_to_pressable(token) for token in _split_hotkey_tokens(hotkey)]
    for key in keys:
        _CONTROLLER.press(key)
    for key in reversed(keys):
        _CONTROLLER.release(key)


class _GlobalHotkeyRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listener: keyboard.GlobalHotKeys | None = None
        self._next_handle = 1
        self._handle_to_hotkey: dict[int, str] = {}
        self._callbacks: dict[str, dict[int, Callable[[], None]]] = defaultdict(dict)

    def _build_listener_map(self) -> dict[str, Callable[[], None]]:
        listener_map: dict[str, Callable[[], None]] = {}
        for hotkey in self._callbacks:
            listener_map[hotkey] = lambda hk=hotkey: self._dispatch(hk)
        return listener_map

    def _dispatch(self, hotkey: str) -> None:
        with self._lock:
            callbacks = list(self._callbacks.get(hotkey, {}).values())
        for callback in callbacks:
            callback()

    def _restart_listener(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        if not self._callbacks:
            return
        self._listener = keyboard.GlobalHotKeys(self._build_listener_map())
        self._listener.start()

    def add_hotkey(self, hotkey: str, callback: Callable[[], None]) -> int:
        normalized = normalize_hotkey(hotkey)
        with self._lock:
            handle = self._next_handle
            self._next_handle += 1
            self._handle_to_hotkey[handle] = normalized
            self._callbacks[normalized][handle] = callback
            self._restart_listener()
            return handle

    def remove_hotkey(self, handle: int) -> None:
        with self._lock:
            hotkey = self._handle_to_hotkey.pop(handle)
            callbacks = self._callbacks.get(hotkey)
            if callbacks is None:
                return
            callbacks.pop(handle, None)
            if not callbacks:
                self._callbacks.pop(hotkey, None)
            self._restart_listener()


_REGISTRY = _GlobalHotkeyRegistry()


def add_hotkey(hotkey: str, callback: Callable[[], None]) -> int:
    return _REGISTRY.add_hotkey(hotkey, callback)


def remove_hotkey(handle: int) -> None:
    _REGISTRY.remove_hotkey(handle)
