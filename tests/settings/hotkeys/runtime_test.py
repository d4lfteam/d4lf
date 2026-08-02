import typing

import pytest

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from pynput import keyboard

from src.settings.hotkeys import runtime as hotkeys


class _FakeListener:
    instances = []

    def __init__(self, on_press, on_release):
        self._on_press = on_press
        self._on_release = on_release
        self.started = False
        self.stopped = False
        self.canonicalized_keys = []
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def canonical(self, key):
        self.canonicalized_keys.append(key)
        if key in {keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.alt, keyboard.Key.cmd}:
            return key
        if key in {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}:
            return keyboard.Key.ctrl
        if key in {keyboard.Key.shift_l, keyboard.Key.shift_r}:
            return keyboard.Key.shift
        if key in {keyboard.Key.alt_l, keyboard.Key.alt_r}:
            return keyboard.Key.alt
        if key in {keyboard.Key.cmd_l, keyboard.Key.cmd_r}:
            return keyboard.Key.cmd
        if isinstance(key, keyboard.Key) and key.value.vk is not None:
            return keyboard.KeyCode.from_vk(key.value.vk)
        return key

    def press(self, key):
        self._on_press(key)

    def release(self, key):
        self._on_release(key)


class TestGlobalHotkeyRegistry:
    @pytest.fixture(autouse=True)
    def setup(self, mocker: MockerFixture):
        _FakeListener.instances = []
        mocker.patch.object(hotkeys.keyboard, "Listener", _FakeListener)
        self.registry = hotkeys._GlobalHotkeyRegistry()
        self.dispatched = []

    @property
    def listener(self):
        return _FakeListener.instances[-1]

    @staticmethod
    def f11_key():
        return keyboard.KeyCode.from_vk(keyboard.Key.f11.value.vk)

    def add_hotkey(self, hotkey):
        return self.registry.add_hotkey(hotkey, lambda: self.dispatched.append(hotkey))

    def test_unmodified_hotkey_dispatches_once(self):
        self.add_hotkey("f11")

        self.listener.press(self.f11_key())

        assert self.dispatched == ["f11"]

    def test_modified_hotkey_does_not_dispatch_unmodified_hotkey(self):
        self.add_hotkey("f11")
        self.add_hotkey("shift+f11")

        self.listener.press(keyboard.Key.shift)
        self.listener.press(self.f11_key())

        assert self.dispatched == ["shift+f11"]

    def test_unmodified_hotkey_does_not_dispatch_when_extra_modifier_is_held(self):
        self.add_hotkey("f11")

        self.listener.press(keyboard.Key.shift)
        self.listener.press(self.f11_key())

        assert self.dispatched == []

    def test_most_specific_hotkey_dispatches_when_multiple_modified_hotkeys_share_key(self):
        self.add_hotkey("ctrl+f11")
        self.add_hotkey("shift+f11")
        self.add_hotkey("ctrl+shift+f11")

        self.listener.press(keyboard.Key.ctrl)
        self.listener.press(keyboard.Key.shift)
        self.listener.press(self.f11_key())

        assert self.dispatched == ["ctrl+shift+f11"]

    def test_key_repeat_does_not_dispatch_active_hotkey_again(self):
        self.add_hotkey("shift+f11")

        self.listener.press(keyboard.Key.shift)
        self.listener.press(self.f11_key())
        self.listener.press(self.f11_key())

        assert self.dispatched == ["shift+f11"]

    def test_hotkey_rearms_after_release(self):
        self.add_hotkey("shift+f11")

        self.listener.press(keyboard.Key.shift)
        self.listener.press(self.f11_key())
        self.listener.release(self.f11_key())
        self.listener.press(self.f11_key())

        assert self.dispatched == ["shift+f11", "shift+f11"]

    def test_releasing_modifier_rearms_modified_hotkey(self):
        self.add_hotkey("shift+f11")

        self.listener.press(keyboard.Key.shift)
        self.listener.press(self.f11_key())
        self.listener.release(keyboard.Key.shift)
        self.listener.press(keyboard.Key.shift)

        assert self.dispatched == ["shift+f11", "shift+f11"]

    def test_left_and_right_modifier_events_are_canonicalized(self):
        self.add_hotkey("shift+f11")

        self.listener.press(keyboard.Key.shift_l)
        self.listener.press(self.f11_key())
        self.listener.release(keyboard.Key.shift_r)
        self.listener.press(keyboard.Key.shift_r)

        assert self.dispatched == ["shift+f11", "shift+f11"]
        assert self.listener.canonicalized_keys == [
            keyboard.Key.shift_l,
            self.f11_key(),
            keyboard.Key.shift_r,
            keyboard.Key.shift_r,
        ]

    def test_multiple_callbacks_for_same_hotkey_dispatch_together(self):
        self.add_hotkey("f11")
        self.add_hotkey("f11")

        self.listener.press(self.f11_key())

        assert self.dispatched == ["f11", "f11"]

    def test_removing_one_callback_keeps_remaining_callback_registered(self):
        first_handle = self.add_hotkey("f11")
        self.add_hotkey("f11")

        self.registry.remove_hotkey(first_handle)
        self.listener.press(self.f11_key())

        assert self.dispatched == ["f11"]

    def test_removing_last_callback_stops_listener_and_clears_hotkey(self):
        handle = self.add_hotkey("f11")
        active_listener = self.listener

        self.registry.remove_hotkey(handle)

        assert active_listener.stopped
        assert self.registry._listener is None
        assert self.registry._callbacks == {}
        assert self.registry._hotkey_keys == {}

    def test_restart_clears_pressed_and_active_state(self):
        self.add_hotkey("shift+f11")
        self.listener.press(keyboard.Key.shift)

        self.add_hotkey("ctrl+f11")

        assert self.registry._pressed_keys == set()
        assert self.registry._active_hotkeys == set()


def test_controller_is_constructed_on_first_key_action(mocker: MockerFixture):
    controller = mocker.Mock()
    constructor = mocker.patch.object(hotkeys.keyboard, "Controller", return_value=controller)
    mocker.patch.object(hotkeys, "_CONTROLLER", None)

    hotkeys.press("a")

    constructor.assert_called_once_with()
    controller.press.assert_called_once_with("a")
