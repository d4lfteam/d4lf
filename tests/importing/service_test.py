import pytest

from src.importing import UnsupportedImportSourceError, select_source


@pytest.mark.parametrize(("url", "name"), [("https://maxroll.gg/x", "maxroll"), ("https://d4builds.gg/x", "d4builds")])
def test_select_source_uses_public_adapter_facades(url: str, name: str) -> None:
    assert select_source(url).name == name


def test_select_source_rejects_unknown_hosts() -> None:
    with pytest.raises(UnsupportedImportSourceError):
        select_source("https://example.invalid/build")
