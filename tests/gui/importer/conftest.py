import os
import pathlib
import tempfile

import pytest
from seleniumbase import Driver
from seleniumbase.core.browser_launcher import override_driver_dir as seleniumbase_override_driver_dir

from src.gui.importer import gui_common


@pytest.fixture
def isolate_uc_driver_dir(monkeypatch) -> None:
    driver_dir = (
        pathlib.Path(tempfile.gettempdir())
        / "d4lf"
        / "seleniumbase-drivers"
        / f"{os.getenv('PYTEST_XDIST_WORKER', 'main')}-{os.getpid()}"
    )
    driver_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        gui_common,
        "Driver",
        lambda *args, **kwargs: seleniumbase_override_driver_dir(str(driver_dir)) or Driver(*args, **kwargs),
    )
