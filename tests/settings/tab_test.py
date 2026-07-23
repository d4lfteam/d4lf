import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.settings.tab import ConfigTab


def test_config_tab_can_be_constructed(qapp, isolated_ini_loader) -> None:
    tab = ConfigTab()
    assert tab.nav_list.count() > 0
    tab.close()
