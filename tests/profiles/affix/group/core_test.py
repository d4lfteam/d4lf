import importlib
import os
import time

import pytest
from PyQt6.QtWidgets import QApplication, QDialog

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import src.profiles.affix.group.pools as pools_module
from src.profiles import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel
from src.profiles.affix.group import AffixGroupEditor


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_group_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.affix.group.core")
    assert hasattr(module, "AffixGroupEditor")


def test_affix_group_editor_lazily_loads_pools_on_expansion(qapp, mock_ini_loader) -> None:
    pool = AffixFilterCountModel(
        count=[AffixFilterModel(name="movement_speed", want_greater=True)], min_count=1, max_count=1
    )
    config = ItemFilterModel(affix_pool=[pool], inherent_pool=[])

    editor = AffixGroupEditor(DynamicItemFilterModel(root={"sword": config}))
    assert editor.greater_count_label.text() == "(1 greater affix marked)"

    time.sleep(0.15)
    qapp.processEvents()

    assert editor.affix_pool_layout.count() == 0
    assert editor.inherent_pool_layout.count() == 0

    editor.affix_pool_container.expand()

    assert editor.affix_pool_layout.count() == 1
    assert editor.inherent_pool_layout.count() == 0


def test_affix_group_editor_pool_mutations_initialize_collapsed_containers(qapp, mock_ini_loader, mocker) -> None:
    pool = AffixFilterCountModel(count=[AffixFilterModel(name="movement_speed")], min_count=1, max_count=1)
    config = ItemFilterModel(affix_pool=[pool], inherent_pool=[])
    editor = AffixGroupEditor(DynamicItemFilterModel(root={"sword": config}))

    editor.add_affix_pool()

    assert len(config.affix_pool) == 2
    assert editor.affix_pool_layout.count() == 2

    class AcceptedDelete:
        def __init__(self, *_args) -> None:
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_value(self):
            return ["Count 0"]

    mocker.patch.object(pools_module, "DeleteAffixPool", AcceptedDelete)
    editor.remove_selected(editor.affix_pool_layout)

    assert len(config.affix_pool) == 1
    assert editor.affix_pool_layout.count() == 1
