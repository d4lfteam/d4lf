from src.settings.tab_mixin import ConfigTabMixin


def test_config_tab_mixin_exposes_setting_generation_operations() -> None:
    assert callable(ConfigTabMixin._filter_settings)
    assert callable(ConfigTabMixin._save_setting_value)
