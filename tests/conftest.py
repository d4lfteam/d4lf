import pytest
from pytest_mock import MockerFixture

from src.config.loader import IniConfigLoader
from src.config.models import BrowserType


@pytest.fixture()
def mock_ini_loader(mocker: MockerFixture):
    general_mock = mocker.patch.object(IniConfigLoader(), "_general")
    general_mock.language = "enUS"
    general_mock.browser = BrowserType.edge
    general_mock.full_dump = False
    return IniConfigLoader()
