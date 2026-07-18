from src.item import FilterResult, Item, ItemRarity, MatchedFilter
from src.loot._fast import create_match_text, fast_feedback


def test_fast_mode_match_text_preserves_affix_aspect_and_set_feedback():
    result = create_match_text([MatchedFilter("Build", aspect_match=True, set_match=True)])

    assert result == ["Build\n  - Aspect\n  - Set"]


def test_fast_mode_reports_junk_at_tooltip_level():
    text, color = fast_feedback(Item(), FilterResult(keep=False, matched=[]))

    assert text == "Junk"
    assert color == "#fc2323"


def test_fast_mode_reports_unfiltered_unique_as_kept():
    text, color = fast_feedback(Item(rarity=ItemRarity.Unique), FilterResult(keep=True, matched=[]))

    assert text == "Unique"
    assert color == "#23fc5d"
