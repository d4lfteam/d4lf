import pytest
from PyQt6.QtWidgets import QApplication

from src.profiles import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel
from src.profiles.affix.group import AffixGroupEditor


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_affix_group_editor_wires_shared_pool_controls(qapp, mock_ini_loader, fake_settings) -> None:
    pool = AffixFilterCountModel(
        count=[AffixFilterModel(name="movement_speed", want_greater=True)], min_count=1, max_count=1
    )
    config = ItemFilterModel(affix_pool=[pool], inherent_pool=[])
    editor = AffixGroupEditor(DynamicItemFilterModel(root={"sword": config}))

    assert editor.greater_controls.count_label.text() == "(1 greater affix marked)"
    editor.greater_controls.auto_sync_checkbox.setChecked(True)
    assert fake_settings == {"auto_sync_ga_affix_sword": True}
    assert config.min_greater_affix_count == 1

    editor.inherent_pools.add_pool()
    assert len(config.inherent_pool) == 1
    assert len(config.affix_pool) == 1
