from src.tools.data_generation.constants import GEAR_TYPES, SIGIL_RARITY_COLOR_TAGS


def test_generation_constants_are_nonempty() -> None:
    assert GEAR_TYPES
    assert SIGIL_RARITY_COLOR_TAGS
