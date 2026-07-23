from src.importing import ImportOptions, ImportRequest
from src.importing.d4builds import import_d4builds


def test_d4builds_facade_rejects_non_d4builds_urls(mocker) -> None:
    request = ImportRequest(url="https://example.invalid/build", options=ImportOptions())

    assert import_d4builds(request, driver=mocker.Mock()) is None
