from src import loot


def test_loot_facade_exposes_filtering_and_colors():
    assert {"create_vision_mode", "run_loot_filter", "get_filter_colors"} <= set(loot.__all__)
    assert isinstance(loot.get_filter_colors(), loot.FilterColors)
