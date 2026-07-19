import sys
import typing

import pytest

from src.settings import BrowserType, get_settings

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Skip Windows-only test modules on non-Windows platforms
WINDOWS_ONLY_MODULES = ["info_overlay_test.py", "paragon_overlay_test.py", "test_sigils_tab.py"]


def pytest_ignore_collect(collection_path, config):
    """Ignore Windows-only test files on non-Windows platforms during collection."""
    if sys.platform != "win32":
        # Check if the file is in our Windows-only list
        if collection_path.name in WINDOWS_ONLY_MODULES:
            return True
    return False


@pytest.fixture
def mock_ini_loader(mocker: MockerFixture):
    settings = get_settings()
    mocker.patch.object(settings.general, "language", "enUS")
    mocker.patch.object(settings.general, "browser", BrowserType.edge)
    mocker.patch.object(settings.general, "full_dump", False)
    return settings
