import pytest
from pytest_mock import MockerFixture

from src.dataloader import Dataloader
from src.gui.importer.maxroll import import_maxroll

URLS = [
    "https://maxroll.gg/d4/build-guides/double-swing-barbarian-guide",
    "https://maxroll.gg/d4/build-guides/evade-spiritborn-build-guide",
    "https://maxroll.gg/d4/build-guides/frozen-orb-sorcerer-guide",
    "https://maxroll.gg/d4/build-guides/minion-necromancer-guide",
    "https://maxroll.gg/d4/build-guides/quill-volley-spiritborn-guide",
    "https://maxroll.gg/d4/build-guides/touch-of-death-spiritborn-guide",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
def test_import_maxroll(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    import_maxroll(url=url)
