import pytest
from pytest_mock import MockerFixture

from src.dataloader import Dataloader
from src.gui.importer.diablo_trade import import_diablo_trade

URLS = [
    "https://diablo.trade/listings/items?exactPrice=true&rarity=legendary&sold=true&sort=newest",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.selenium
def test_import_diablo_trade(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    import_diablo_trade(url=url, max_listings=30)
