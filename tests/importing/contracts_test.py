from src.importing.contracts import ImportOptions, ImportRequest


def test_import_request_strips_url_and_normalizes_options() -> None:
    request = ImportRequest("  https://example.invalid/build\n", ImportOptions(filename_parts=("source",)))
    assert request.url == "https://example.invalid/build"
    assert request.filename_parts[0].value == "source"


def test_import_options_include_charms_and_seals_by_default() -> None:
    options = ImportOptions()

    assert options.import_charms
    assert options.import_seals


def test_import_request_preserves_charm_and_seal_choices() -> None:
    request = ImportRequest("https://example.invalid/build", ImportOptions(import_charms=False, import_seals=False))

    assert not request.options.import_charms
    assert not request.options.import_seals
