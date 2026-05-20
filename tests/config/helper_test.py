import pytest

from src.config.helper import singleton, str_to_int_list, to_keyboard_hotkey, validate_hotkey
from src.config.settings_models import AdvancedOptionsModel


class TestKeyMustExist:
    def test_existing_key(self):
        # Test for an existing key
        assert validate_hotkey("a")

    def test_modifier_key_works(self):
        assert validate_hotkey("shift+a")

    @pytest.mark.parametrize("hotkey", ["left", "right", "up", "down", "shift+left", "ctrl+right", "alt+up"])
    def test_arrow_keys_work(self, hotkey):
        assert validate_hotkey(hotkey, allow_empty=True)

    def test_layout_sensitive_key_uses_scan_code_for_keyboard_hook(self, monkeypatch):
        umlaut_key = "ctrl+\N{LATIN SMALL LETTER O WITH DIAERESIS}"

        def fake_parse_hotkey(hotkey):
            return {umlaut_key: (((29, 57373), (39,)),), "^": (((41, -255),),)}[hotkey]

        monkeypatch.setattr("src.config.helper.keyboard.parse_hotkey", fake_parse_hotkey)

        assert to_keyboard_hotkey(umlaut_key) == (((29, 57373), (39,)),)
        assert to_keyboard_hotkey("^") == (((41,),),)

    def test_empty_key_disables_optional_hotkey(self):
        assert not validate_hotkey("", allow_empty=True)

    def test_empty_key_fails_by_default(self):
        with pytest.raises(ValueError, match="Can only normalize non-empty string names."):
            validate_hotkey("")

    def test_non_existing_key(self):
        # Test for a non-existing key
        with pytest.raises(ValueError, match="Key 'non_existing_key' is not mapped to any known key."):
            validate_hotkey("non_existing_key")

    def test_empty_keys_are_excluded_from_unique_hotkey_check(self):
        model = AdvancedOptionsModel(exit_key="", toggle_paragon_overlay="")

        assert not model.exit_key
        assert not model.toggle_paragon_overlay

    def test_non_empty_keys_must_still_be_unique(self):
        with pytest.raises(ValueError, match="hotkeys must be unique"):
            AdvancedOptionsModel(exit_key="f10", toggle_paragon_overlay="f10")


class TestSingletonDecorator:
    @singleton
    class SingletonDummyClass:
        def __init__(self, *args, **kwargs):
            pass

    def test_singleton_instance(self):
        # Test whether multiple instances of singleton class return the same object
        instance1 = self.SingletonDummyClass()
        instance2 = self.SingletonDummyClass()
        assert instance1 is instance2


class TestStrToIntList:
    def test_empty_string(self):
        # Test for an empty string
        assert str_to_int_list("") == []

    def test_single_integer(self):
        # Test for a single integer string
        assert str_to_int_list("5") == [5]

    def test_multiple_integers(self):
        # Test for a string containing multiple integers separated by commas
        assert str_to_int_list("1,2,3,4,5") == [1, 2, 3, 4, 5]

    def test_invalid_input(self):
        # Test for invalid input type
        with pytest.raises(ValueError, match="invalid literal"):
            str_to_int_list("1,2,3,a,5")

    def test_negative_numbers(self):
        # Test for negative numbers
        assert str_to_int_list("-1,-2,-3,-4,-5") == [-1, -2, -3, -4, -5]

    def test_whitespace(self):
        # Test for string containing whitespace
        assert str_to_int_list(" 1 ,  2 , 3 , 4 , 5 ") == [1, 2, 3, 4, 5]
