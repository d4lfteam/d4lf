from src.importing.contracts import ImportOptions, ImportRequest


def test_import_request_strips_url_and_normalizes_options() -> None:
    request = ImportRequest("  https://example.invalid/build\n", ImportOptions(filename_parts=("source",)))
    assert request.url == "https://example.invalid/build"
    assert request.filename_parts[0].value == "source"
