import typing

import pytest

from src.importing import ImportOptions, ImportRequest
from src.importing.d4builds import adapter as d4builds_module
from src.item import Dataloader
from tests.conftest import D4BUILDS_IMPORT_URLS

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize("url", D4BUILDS_IMPORT_URLS)
def test_import_d4builds(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()  # need to load data first or the mock will make it impossible
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
