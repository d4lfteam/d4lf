from src.importing import ImportOptions, ImportRequest, ImportSourceError
from src.importing.mobalytics import MobalyticsError, import_mobalytics


def test_mobalytics_facade_rejects_non_mobalytics_urls(mocker) -> None:
    request = ImportRequest(url="https://example.invalid/build", options=ImportOptions())

    assert import_mobalytics(request, driver=mocker.Mock()) is None
    assert issubclass(MobalyticsError, Exception)
    assert issubclass(MobalyticsError, ImportSourceError)
