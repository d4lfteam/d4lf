import os
from typing import TYPE_CHECKING

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.settings.loader import IniConfigLoader

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def isolated_ini_loader(tmp_path: Path):
    loader = IniConfigLoader()
    original = {
        "user_dir": loader._user_dir,
        "parser": loader._parser,
        "general": loader._general,
        "char": loader._char,
        "advanced_options": loader._advanced_options,
        "signature": loader._last_config_signature,
        "revision": loader._config_revision,
        "listeners": list(loader._change_listeners),
        "logs": list(loader._deferred_cleanup_log_records),
        "defer_logs": loader._defer_cleanup_log_records,
    }
    loader._user_dir = tmp_path
    loader._change_listeners = []
    loader._deferred_cleanup_log_records = []
    loader._defer_cleanup_log_records = True
    loader.load(clear=True)
    try:
        yield loader
    finally:
        loader._user_dir = original["user_dir"]
        loader._parser = original["parser"]
        loader._general = original["general"]
        loader._char = original["char"]
        loader._advanced_options = original["advanced_options"]
        loader._last_config_signature = original["signature"]
        loader._config_revision = original["revision"]
        loader._change_listeners = original["listeners"]
        loader._deferred_cleanup_log_records = original["logs"]
        loader._defer_cleanup_log_records = original["defer_logs"]
