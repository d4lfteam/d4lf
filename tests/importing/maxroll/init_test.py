from src.importing import ImportOptions, ImportRequest
from src.importing.maxroll import import_maxroll


def test_maxroll_facade_rejects_non_maxroll_urls() -> None:
    request = ImportRequest(url="https://example.invalid/build", options=ImportOptions())

    assert import_maxroll(request) is None
