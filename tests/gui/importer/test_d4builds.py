import pytest
from pytest_mock import MockerFixture

from src.dataloader import Dataloader
from src.gui.importer.d4builds import import_d4builds

URLS = [
    "https://d4builds.gg/builds/01953e1c-6ba5-4f3a-8ebe-73273beda61b",
    "https://d4builds.gg/builds/0704c20f-68a7-49ed-97da-fc51454a9906",
    "https://d4builds.gg/builds/23ae9cbb-933e-4a88-999c-2241654cc8e2",
    "https://d4builds.gg/builds/a3e80fe0-11a8-48b8-8255-f6540ebc1c1d",
    "https://d4builds.gg/builds/b0330cfb-0f79-4d6d-a362-129492fad6a9",
    "https://d4builds.gg/builds/ba06ccf8-4182-449a-bfb4-102f96b1041e",
    "https://d4builds.gg/builds/dbad6569-2e78-4c43-a831-c563d0a1e1ad",
    "https://d4builds.gg/builds/ef414fbd-81cd-49d1-9c8d-4938b278e2ee",
    "https://d4builds.gg/builds/f8298a54-dc67-41ab-8232-ddfd32bd80fa",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.selenium()
def test_import_d4builds(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    import_d4builds(url=url)
