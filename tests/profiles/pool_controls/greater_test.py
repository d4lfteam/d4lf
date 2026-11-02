import pytest
from PyQt6.QtWidgets import QApplication

from src.profiles import AffixFilterCountModel, AffixFilterModel, CharmFilterModel
from src.profiles.pool_controls import GreaterAffixControls


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _config(*want_greater: bool) -> CharmFilterModel:
    affixes = [AffixFilterModel(name="movement_speed", want_greater=flag) for flag in want_greater]
    return CharmFilterModel(affix_pool=[AffixFilterCountModel(count=affixes, min_count=1, max_count=3)])


def test_shows_marked_count_and_writes_min_greater_to_config(qapp, mock_ini_loader) -> None:
    config = _config(True, True)
    controls = GreaterAffixControls(config, "charm_build")

    assert controls.count_label.text() == "(2 greater affixes marked)"
    controls.min_greater.setValue(3)
    assert config.min_greater_affix_count == 3


def test_auto_sync_follows_marked_affixes_and_persists(qapp, mock_ini_loader, fake_settings) -> None:
    config = _config(True, False)
    controls = GreaterAffixControls(config, "charm_build")

    controls.auto_sync_checkbox.setChecked(True)
    assert fake_settings == {"auto_sync_ga_charm_build": True}
    assert not controls.min_greater.isEnabled()
    assert config.min_greater_affix_count == 1

    config.affix_pool[0].count[1].want_greater = True
    controls.refresh()
    assert controls.count_label.text() == "(2 greater affixes marked)"
    assert config.min_greater_affix_count == 2

    assert GreaterAffixControls(config, "charm_build").auto_sync_checkbox.isChecked()
    assert not GreaterAffixControls(config, "seal_build").auto_sync_checkbox.isChecked()


def test_set_min_greater_skips_auto_synced_controls(qapp, mock_ini_loader) -> None:
    config = _config(False)
    controls = GreaterAffixControls(config, "charm_build")

    controls.set_min_greater(2)
    assert config.min_greater_affix_count == 2

    controls.auto_sync_checkbox.setChecked(True)
    controls.set_min_greater(4)
    assert config.min_greater_affix_count == 0
