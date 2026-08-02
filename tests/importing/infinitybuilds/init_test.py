from src.importing import ImportOptions, ImportRequest, ImportSourceError
from src.importing.infinitybuilds import InfinityBuildsError, import_infinitybuilds


def test_infinitybuilds_facade_rejects_non_infinitybuilds_urls(mocker) -> None:
    request = ImportRequest(url="https://example.invalid/build", options=ImportOptions())

    assert import_infinitybuilds(request, driver=mocker.Mock()) is None
    assert issubclass(InfinityBuildsError, Exception)
    assert issubclass(InfinityBuildsError, ImportSourceError)
