from src import loot


def test_loot_facade_exposes_filtering_orchestration_and_mode_selection():
    assert callable(loot.create_vision_mode)
    assert callable(loot.run_loot_filter)


def test_loot_facade_exposes_shared_filter_colors():
    assert isinstance(loot.get_filter_colors(), loot.FilterColors)
