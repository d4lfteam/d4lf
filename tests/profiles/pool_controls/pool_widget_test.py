import pytest
from PyQt6.QtWidgets import QApplication

from src.profiles import AffixFilterCountModel, AffixFilterModel
from src.profiles.pool_controls import AffixPoolWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_affix_pool_add_and_remove_lifecycle(qapp, mock_ini_loader) -> None:
    affix = AffixFilterModel(name="movement_speed")
    pool = AffixFilterCountModel(count=[affix], min_count=1, max_count=3)
    widget = AffixPoolWidget(pool)

    assert widget.affix_list.count() == 1
    widget.add_affix()
    assert len(pool.count) == 2
    assert widget.affix_list.count() == 2

    item = widget.affix_list.item(0)
    assert item is not None
    item.setSelected(True)
    widget.remove_selected(widget.affix_list)
    assert len(pool.count) == 1
    assert widget.affix_list.count() == 1
