import os
import typing

import pytest

from src.dataloader import Dataloader
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import import_maxroll

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

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
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_maxroll(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    config = ImportConfig(url, True, True, False, "")
    import_maxroll(config=config)
