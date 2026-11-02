import os

import pytest
from PyQt6.QtWidgets import QApplication, QDialog

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.profiles import AffixFilterCountModel, AffixFilterModel
from src.profiles.pool_controls import AffixPoolSection


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _pool() -> AffixFilterCountModel:
    return AffixFilterCountModel(count=[AffixFilterModel(name="movement_speed")], min_count=1, max_count=1)


def test_add_and_remove_pools_keep_config_aligned(qapp, mock_ini_loader, mocker) -> None:
    pools = [_pool()]
    section = AffixPoolSection("Affix Pool", pools, default_affix="maximum_life")

    section.add_pool()
    assert len(pools) == 2
    assert pools[1].count[0].name == "maximum_life"

    dialog = mocker.patch("src.profiles.pool_controls.affix_pools.SelectToDeleteDialog").return_value
    dialog.exec.return_value = QDialog.DialogCode.Accepted
    dialog.get_value.return_value = [0]
    removed = mocker.Mock()
    section.pools_removed.connect(removed)

    section.remove_pools()

    assert pools[0].count[0].name == "maximum_life"
    assert len(pools) == 1
    removed.assert_called_once()


def test_convert_to_min_percent_loads_collapsed_pools(qapp, mock_ini_loader) -> None:
    pools = [_pool()]
    section = AffixPoolSection("Affix Pool", pools, default_affix="movement_speed")

    section.convert_to_min_percent(80)

    assert pools[0].count[0].min_percent_of_affix == 80
