import os
import sys
import typing

import pytest

from src.settings import BrowserType, get_settings

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Skip Windows-only test modules on non-Windows platforms
WINDOWS_ONLY_MODULES = ["info_overlay_test.py", "paragon_overlay_test.py", "test_sigils_tab.py"]
IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
EXTERNAL_IMPORTER_MARKERS = ("selenium",)
EXTERNAL_IMPORTER_NODE_MARKERS = {
    "tests/importing/d4builds/adapter_test.py::test_import_d4builds": ("selenium",),
    "tests/importing/infinitybuilds/paragon_test.py::test_import_infinitybuilds": ("selenium",),
    "tests/importing/mobalytics/adapter_test.py::test_import_mobalytics": ("selenium",),
}
D4BUILDS_IMPORT_URLS = (
    "https://d4builds.gg/builds/ancients-barbarian-endgame/",
    "https://d4builds.gg/builds/charge-barbarian-endgame",
    "https://d4builds.gg/builds/firewall-sorcerer-endgame",
    "https://d4builds.gg/builds/leap-rend-barbarian-endgame",
    "https://d4builds.gg/builds/penetrating-shot-rogue-endgame",
    "https://d4builds.gg/builds/pestilent-swarm-spiritborn-endgame",
    "https://d4builds.gg/builds/rain-of-arrows-rogue-endgame",
    "https://d4builds.gg/builds/shred-druid-endgame",
    "https://d4builds.gg/builds/whirlwind-barbarian-endgame",
)
INFINITYBUILDS_IMPORT_URLS = ("https://infinitybuilds.gg/en/builds/barbarian-fL8P6vVSqI",)
MAXROLL_IMPORT_URLS = (
    "https://maxroll.gg/d4/build-guides/auradin-guide",
    "https://maxroll.gg/d4/build-guides/blessed-hammer-paladin-guide",
    "https://maxroll.gg/d4/build-guides/double-swing-barbarian-guide",
    "https://maxroll.gg/d4/build-guides/evade-spiritborn-build-guide",
    "https://maxroll.gg/d4/build-guides/frozen-orb-sorcerer-guide",
    "https://maxroll.gg/d4/build-guides/minion-necromancer-guide",
    "https://maxroll.gg/d4/build-guides/shield-of-retribution-paladin-guide",
    "https://maxroll.gg/d4/planner/ce9zox0y#3",
)
MOBALYTICS_IMPORT_URLS = (
    "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb",
    "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb?ws-ngf5-1=activeVariantId%2C7a9c6d51-18e9-4090-a804-7b73ff00879d",
    "https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
    "https://mobalytics.gg/diablo-4/builds/rogue-efficientrogue-dance-of-knives?ws-ngf5-1=activeVariantId%2Ca2977139-f3e2-4b13-aa64-82ba69972528",
)


def pytest_ignore_collect(collection_path, config):
    """Ignore Windows-only test files on non-Windows platforms during collection."""
    if sys.platform != "win32":
        # Check if the file is in our Windows-only list
        if collection_path.name in WINDOWS_ONLY_MODULES:
            return True
    return False


def pytest_collection_modifyitems(config, items):
    """Mark and skip external importer tests outside GitHub Actions."""
    skip_external_importer = pytest.mark.skip(reason="Importer tests are skipped if not run from Github Actions")
    for item in items:
        for nodeid_prefix, markers in EXTERNAL_IMPORTER_NODE_MARKERS.items():
            if item.nodeid == nodeid_prefix or item.nodeid.startswith(f"{nodeid_prefix}["):
                for marker in markers:
                    item.add_marker(getattr(pytest.mark, marker))
                break
        if not IN_GITHUB_ACTIONS and any(item.get_closest_marker(marker) for marker in EXTERNAL_IMPORTER_MARKERS):
            item.add_marker(skip_external_importer)


@pytest.fixture
def mock_ini_loader(mocker: MockerFixture):
    settings = get_settings()
    mocker.patch.object(settings.general, "language", "enUS")
    mocker.patch.object(settings.general, "browser", BrowserType.chrome)
    mocker.patch.object(settings.general, "full_dump", False)
    return settings
