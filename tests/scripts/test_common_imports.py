import importlib
import sys


def test_scripts_common_imports_without_keyboard(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyboard", None)
    sys.modules.pop("src.scripts.common", None)

    common = importlib.import_module("src.scripts.common")

    common.mark_as_junk()
    common.mark_as_favorite()
    common.drop_item_from_inventory()
