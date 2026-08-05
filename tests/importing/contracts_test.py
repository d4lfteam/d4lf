from src.importing.contracts import FilenamePart, ImportOptions, ImportRequest, ImportSession


def test_import_request_strips_url_and_normalizes_options() -> None:
    request = ImportRequest("  https://example.invalid/build\n", ImportOptions(filename_parts=("source",)))
    assert request.url == "https://example.invalid/build"
    assert request.filename_parts[0].value == "source"


def test_import_request_normalizes_filename_parts() -> None:
    request = ImportRequest("url", ImportOptions(filename_parts=("class",)))

    assert request.filename_parts == (FilenamePart.CLASS,)


def test_import_options_include_charms_and_seals_by_default() -> None:
    options = ImportOptions()

    assert options.import_charms
    assert options.import_seals


def test_import_request_preserves_charm_and_seal_choices() -> None:
    request = ImportRequest("https://example.invalid/build", ImportOptions(import_charms=False, import_seals=False))

    assert not request.options.import_charms
    assert not request.options.import_seals


def test_variant_selection_is_immutable_and_normalizes_ids() -> None:
    request = ImportRequest("https://example.invalid/build").with_variant_selection(("1", "2"))
    selection = request.variant_selection

    assert selection is not None
    assert selection.ids == ("1", "2")
    assert "1" in selection
    assert bool(selection)


def test_import_session_retains_source_and_closes_idempotently() -> None:
    class FakeSource:
        name = "fixture"
        close_calls = 0

        def fetch_variants(self, request):
            return []

        def import_build(self, request):
            raise AssertionError

        def close(self):
            self.close_calls += 1

    source = FakeSource()
    session = ImportSession(source)

    assert session.source is source
    session.close()
    session.close()

    assert source.close_calls == 1
    assert session.closed
