"""pynput-backed keyboard operations for the settings hotkey seam."""

import threading
from collections import defaultdict
from typing import TYPE_CHECKING, cast

from pynput import keyboard

from src.settings.binding.core import _canonicalize_token, _split_hotkey_tokens, normalize_hotkey

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable

_CONTROLLER: keyboard.Controller | None = None


def _controller() -> keyboard.Controller:
    global _CONTROLLER
    if _CONTROLLER is None:
        _CONTROLLER = keyboard.Controller()
    return _CONTROLLER


def _to_pressable(token: str) -> str | keyboard.Key:
    canonical_token = _canonicalize_token(token)
    if len(canonical_token) == 1:
        return canonical_token
    return getattr(keyboard.Key, canonical_token)


def press(key: str) -> None:
    _controller().press(_to_pressable(key))


def release(key: str) -> None:
    _controller().release(_to_pressable(key))


def send(hotkey: str) -> None:
    keys = [_to_pressable(token) for token in _split_hotkey_tokens(hotkey)]
    for key in keys:
        _controller().press(key)
    for key in reversed(keys):
        _controller().release(key)


class _GlobalHotkeyRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listener: keyboard.Listener | None = None
        self._next_handle = 1
        self._handle_to_hotkey: dict[int, str] = {}
        self._callbacks: dict[str, dict[int, Callable[[], None]]] = defaultdict(dict)
        self._hotkey_keys: dict[str, frozenset[Hashable]] = {}
        self._pressed_keys: set[Hashable] = set()
        self._active_hotkeys: set[str] = set()

    def _canonicalize_event_key(self, key: Hashable) -> Hashable:
        if self._listener is None:
            return key
        return cast("Hashable", self._listener.canonical(key))

    def _on_press(self, key: Hashable) -> None:
        callbacks: list[Callable[[], None]] = []
        with self._lock:
            canonical_key = self._canonicalize_event_key(key)
            if canonical_key in self._pressed_keys:
                return

            self._pressed_keys.add(canonical_key)
            pressed_keys = frozenset(self._pressed_keys)
            for hotkey, hotkey_keys in self._hotkey_keys.items():
                if hotkey_keys == pressed_keys and hotkey not in self._active_hotkeys:
                    self._active_hotkeys.add(hotkey)
                    callbacks.extend(self._callbacks.get(hotkey, {}).values())

        for callback in callbacks:
            callback()

    def _on_release(self, key: Hashable) -> None:
        with self._lock:
            canonical_key = self._canonicalize_event_key(key)
            self._pressed_keys.discard(canonical_key)
            self._active_hotkeys = {
                hotkey for hotkey in self._active_hotkeys if canonical_key not in self._hotkey_keys[hotkey]
            }

    def _restart_listener(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()
        self._active_hotkeys.clear()
        if not self._callbacks:
            return
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def add_hotkey(self, hotkey: str, callback: Callable[[], None]) -> int:
        normalized = normalize_hotkey(hotkey)
        with self._lock:
            handle = self._next_handle
            self._next_handle += 1
            self._handle_to_hotkey[handle] = normalized
            self._callbacks[normalized][handle] = callback
            self._hotkey_keys[normalized] = frozenset(keyboard.HotKey.parse(normalized))
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
                self._hotkey_keys.pop(hotkey, None)
            self._restart_listener()


_REGISTRY = _GlobalHotkeyRegistry()


def add_hotkey(hotkey: str, callback: Callable[[], None]) -> int:
    return _REGISTRY.add_hotkey(hotkey, callback)


def remove_hotkey(handle: int) -> None:
    _REGISTRY.remove_hotkey(handle)


__all__ = ["add_hotkey", "press", "release", "remove_hotkey", "send"]
