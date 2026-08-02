import typing

import pytest

from src.game_data import GameCatalog
from src.importing import ImportOptions, ImportRequest
from src.importing.d4builds import adapter as d4builds_module
from tests.conftest import D4BUILDS_IMPORT_URLS

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from selenium.webdriver.remote.webdriver import WebDriver


@pytest.mark.parametrize("url", D4BUILDS_IMPORT_URLS)
def test_import_d4builds(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    GameCatalog()  # need to load data first or the mock will make it impossible
    mocker.patch("builtins.open", new=mocker.mock_open())
    request = ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
        ),
    )
    result = d4builds_module.import_d4builds(request=request)

    assert result is not None
    assert result.source_name == "d4builds"


def test_load_variant_page_returns_shared_metadata(mocker: MockerFixture) -> None:
    driver = mocker.Mock(page_source="<html><body>build</body></html>")
    mocker.patch("src.importing.d4builds.adapter.WebDriverWait").return_value.until = mocker.Mock()
    metadata = ("barbarian", "Bash", "12", "Pit Push")
    mocker.patch("src.importing.d4builds.adapter._extract_build_metadata", return_value=metadata)

    loaded = d4builds_module._load_variant_page("https://d4builds.gg/build?var=1", driver)

    assert loaded.class_name == "barbarian"
    assert loaded.build_header == "Bash"
    assert loaded.season_number == "12"
    assert loaded.variant_name == "Pit Push"
    driver.get.assert_called_once_with("https://d4builds.gg/build?var=1")


def test_load_variant_page_waits_before_capturing_hydrated_source(mocker: MockerFixture) -> None:
    events: list[str] = []

    class Driver:
        page_source = property(lambda _self: events.append("read") or "<html><body>build</body></html>")

        def get(self, _url: str) -> None:
            return None

    mocker.patch("src.importing.d4builds.adapter.WebDriverWait").return_value.until = mocker.Mock()
    mocker.patch("src.importing.d4builds.adapter.time.sleep", side_effect=lambda _seconds: events.append("sleep"))
    mocker.patch(
        "src.importing.d4builds.adapter._extract_build_metadata", return_value=("barbarian", "Bash", "12", "Pit Push")
    )

    d4builds_module._load_variant_page(
        "https://d4builds.gg/builds/example-build", typing.cast("WebDriver", Driver()), wait_for_paperdoll=True
    )

    assert events == ["sleep", "read"]


def test_fetch_variant_discovery_is_bounded(mocker: MockerFixture) -> None:
    def load_page(*_args, **_kwargs):
        index = loader.call_count
        return d4builds_module._LoadedVariantPage(
            data=mocker.Mock(),
            class_name="barbarian",
            build_header="Bash",
            season_number="12",
            variant_name=f"Variant {index}",
        )

    loader = mocker.patch("src.importing.d4builds.adapter._load_variant_page", side_effect=load_page)
    request = ImportRequest("https://d4builds.gg/builds/example-build")

    variants = d4builds_module.fetch_variants_d4builds(request, driver=mocker.Mock())

    assert len(variants) == d4builds_module.MAX_VARIANTS
    assert loader.call_count == d4builds_module.MAX_VARIANTS


def test_fetch_variant_discovery_keeps_distinct_unnamed_pages(mocker: MockerFixture) -> None:
    pages = iter([
        d4builds_module._LoadedVariantPage(
            data=d4builds_module.lxml.html.fromstring("<html><body>one</body></html>"),
            class_name="barbarian",
            build_header="Bash",
            season_number="12",
            variant_name="",
        ),
        d4builds_module._LoadedVariantPage(
            data=d4builds_module.lxml.html.fromstring("<html><body>two</body></html>"),
            class_name="barbarian",
            build_header="Bash",
            season_number="12",
            variant_name="",
        ),
        d4builds_module._LoadedVariantPage(
            data=d4builds_module.lxml.html.fromstring("<html><body>two</body></html>"),
            class_name="barbarian",
            build_header="Bash",
            season_number="12",
            variant_name="",
        ),
    ])
    loader = mocker.patch("src.importing.d4builds.adapter._load_variant_page", side_effect=pages)

    variants = d4builds_module.fetch_variants_d4builds(
        ImportRequest("https://d4builds.gg/builds/example-build"), driver=mocker.Mock()
    )

    assert [variant.name for variant in variants] == ["Variant 1", "Variant 2"]
    assert loader.call_count == 3
