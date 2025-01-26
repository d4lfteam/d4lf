import pytest
from pytest_mock import MockerFixture

from src.dataloader import Dataloader
from src.gui.importer.mobalytics import import_mobalytics

URLS = [
    "https://mobalytics.gg/diablo-4/builds/barbarian/barbarian-leveling-guide",
    "https://mobalytics.gg/diablo-4/builds/barbarian/bash?coreTab=assigned-skills&equipmentTab=aspects-and-uniques&variantTab=1",
    "https://mobalytics.gg/diablo-4/builds/barbarian/bash?coreTab=assigned-skills&equipmentTab=aspects-and-uniques&variantTab=2",
    "https://mobalytics.gg/diablo-4/builds/barbarian/ron-array-bash-fury-barb?coreTab=assigned-skills&equipmentTab=aspects-and-uniques&variantTab=0",
    "https://mobalytics.gg/diablo-4/builds/druid/screamhearts-quickshift-tornado",
    "https://mobalytics.gg/diablo-4/builds/druid/wind-shear",
    "https://mobalytics.gg/diablo-4/builds/druid/wind-shear?coreTab=assigned-skills&equipmentTab=aspects-and-uniques&variantTab=1",
    "https://mobalytics.gg/diablo-4/builds/necromancer/p4wnyhof-golem-slammer",
    "https://mobalytics.gg/diablo-4/builds/necromancer/ramping-minions",
    "https://mobalytics.gg/diablo-4/builds/rogue/heartseeker",
    "https://mobalytics.gg/diablo-4/builds/sorcerer/firewall-scorched-earth",
    "https://mobalytics.gg/diablo-4/builds/sorcerer/kripp-s-ultimate-fire-sorc",
    "https://mobalytics.gg/diablo-4/builds/sorcerer/nicktew-s4-blizzard",
    "https://mobalytics.gg/diablo-4/profile/3aeadb5c-522e-47b9-9a17-cdeaaa58909c/builds/4bb9a04e-da1e-449f-91ab-ca29e5727a20",
    "https://mobalytics.gg/diablo-4/profile/bd7d970b-813c-4f98-b8b5-d5ca637f7ec0/builds/9ed37972-f738-4d1e-a231-e9f0f367c848",
]


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests()
def test_import_mobalytics(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    import_mobalytics(url=url)
