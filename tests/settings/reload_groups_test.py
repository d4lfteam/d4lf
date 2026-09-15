from src.settings.reload_groups import LOG_LEVEL_SETTING_KEYS, has_any_changed


def test_has_any_changed_detects_overlap() -> None:
    assert has_any_changed(frozenset({"advanced_options.log_lvl"}), LOG_LEVEL_SETTING_KEYS)


def test_has_any_changed_returns_false_without_overlap() -> None:
    assert not has_any_changed(frozenset({"general.language"}), LOG_LEVEL_SETTING_KEYS)
