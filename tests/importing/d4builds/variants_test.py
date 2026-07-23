from typing import TYPE_CHECKING, cast

import pytest
from lxml import html

from src.importing import ImportRequest
from src.importing.d4builds.metadata import D4BuildsError
from src.importing.d4builds.variants import extract_variant

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


def test_extract_variant_reports_missing_items() -> None:
    with pytest.raises(D4BuildsError, match="No items found"):
        extract_variant(
            data=html.fromstring("<html><body></body></html>"),
            driver=cast("WebDriver", object()),
            request=ImportRequest("https://d4builds.gg/builds/example-build"),
            class_name="barbarian",
            build_header="Bash",
            variant_name="Pit Push",
        )
