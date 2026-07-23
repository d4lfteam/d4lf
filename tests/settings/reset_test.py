from src.settings.reset import ConfigResetMixin


def test_reset_mixin_is_available_as_the_settings_reset_seam() -> None:
    assert hasattr(ConfigResetMixin, "_perform_global_reset")
    assert hasattr(ConfigResetMixin, "_reset_current_category")
