import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.settings.tab import ConfigTab


def test_config_tab_can_be_constructed(qapp, isolated_ini_loader) -> None:
    tab = ConfigTab()
    assert tab.nav_list.count() > 0
    tab.close()


def test_loot_filter_override_switches_explain_mythic_behavior(qapp, isolated_ini_loader) -> None:
    tab = ConfigTab()

    for key in ("equipment", "sigils", "tributes", "seals", "charms"):
        tooltip = tab.model_to_parameter_value_map[f"general.filter_{key}"].toolTip()
        assert "all" in tooltip
        assert "skipped" in tooltip
        assert "including Mythic" in tooltip
        assert "always kept" in tooltip

    tab.close()
