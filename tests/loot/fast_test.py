from src.item import FilterResult, Item, ItemRarity, MatchedFilter
from src.loot.fast import create_match_text, fast_feedback


def test_fast_mode_preserves_match_details_and_feedback():
    assert create_match_text([MatchedFilter("Build", aspect_match=True, set_match=True)]) == [
        "Build\n  - Aspect\n  - Set"
    ]
    assert fast_feedback(Item(), FilterResult(keep=False, matched=[])) == ("Junk", "#fc2323")
    assert fast_feedback(Item(rarity=ItemRarity.Unique), FilterResult(keep=True, matched=[])) == ("Unique", "#23fc5d")
