import pytest

from src.settings.validation import singleton, str_to_int_list, validate_hotkey


class TestKeyMustExist:
    def test_existing_key(self) -> None:
        # Test for an existing key
        assert validate_hotkey("a")

    def test_modifier_key_works(self) -> None:
        assert validate_hotkey("shift+a")

    def test_modifier_hotkey_is_canonicalized(self) -> None:
        assert validate_hotkey("shift+ctrl+f11") == "ctrl+shift+f11"

    def test_pynput_style_hotkey_stays_human_readable(self) -> None:
        assert validate_hotkey("<ctrl>+<shift>+<f11>") == "ctrl+shift+f11"

    def test_mac_command_modifier_works(self) -> None:
        assert validate_hotkey("cmd+f11") == "cmd+f11"

    def test_modifier_only_hotkey_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Hotkey must include at least one non-modifier key."):
            validate_hotkey("ctrl+shift")

    def test_non_existing_key(self) -> None:
        # Test for a non-existing key
        with pytest.raises(ValueError, match="Key 'non_existing_key' is not mapped to any known key."):
            validate_hotkey("non_existing_key")


class TestSingletonDecorator:
    @singleton
    class SingletonDummyClass:
        def __init__(self, *args, **kwargs) -> None:
            pass

    def test_singleton_instance(self) -> None:
        # Test whether multiple instances of singleton class return the same object
        instance1 = self.SingletonDummyClass()
        instance2 = self.SingletonDummyClass()
        assert instance1 is instance2


class TestStrToIntList:
    def test_empty_string(self) -> None:
        # Test for an empty string
        assert str_to_int_list("") == []

    def test_single_integer(self) -> None:
        # Test for a single integer string
        assert str_to_int_list("5") == [5]

    def test_multiple_integers(self) -> None:
        # Test for a string containing multiple integers separated by commas
        assert str_to_int_list("1,2,3,4,5") == [1, 2, 3, 4, 5]

    def test_invalid_input(self) -> None:
        # Test for invalid input type
        with pytest.raises(ValueError, match="invalid literal"):
            str_to_int_list("1,2,3,a,5")

    def test_negative_numbers(self) -> None:
        # Test for negative numbers
        assert str_to_int_list("-1,-2,-3,-4,-5") == [-1, -2, -3, -4, -5]

    def test_whitespace(self) -> None:
        # Test for string containing whitespace
        assert str_to_int_list(" 1 ,  2 , 3 , 4 , 5 ") == [1, 2, 3, 4, 5]
