from PyQt6.QtCore import QObject, pyqtSignal

from src import importing
from src.importing import (
    FilenamePart,
    ImportOptions,
    ImportRequest,
    ImportResult,
    ImportSession,
    ImportSourceError,
    UnsupportedImportSourceError,
    VariantMetadata,
    VariantSelection,
    assemble_profile_file_name,
    import_build,
    open_session,
    select_source,
)
from src.profiles import ProfileModel


def test_import_request_normalizes_filename_parts() -> None:
    request = ImportRequest(
        url="https://example.invalid/build", options=ImportOptions(filename_parts=("source", FilenamePart.VARIANT))
    )

    assert request.options.filename_parts == (FilenamePart.SOURCE, FilenamePart.VARIANT)


def test_facade_exports_variant_selection_contract() -> None:
    selection = VariantSelection.from_ids(("variant-1",))

    assert selection.ids == ("variant-1",)


def test_facade_exposes_source_error_without_leaking_provider_contracts() -> None:
    assert importing.ImportSourceError is ImportSourceError
    assert "D2CoreImportError" not in importing.__all__
    assert "D2CoreImportSource" not in importing.__all__
    assert "canonicalize_d2core_url" not in importing.__all__
    assert not hasattr(importing, "D2CoreImportError")


def test_facade_exports_import_session_lifecycle_contract() -> None:
    assert ImportSession.__name__ == "ImportSession"
    assert open_session.__name__ == "open_session"


def test_filename_assembly_preserves_selected_order_and_title_cleanup() -> None:
    assert (
        assemble_profile_file_name(
            source_name="maxroll",
            class_name="Spiritborn",
            season_number="Season 12",
            build_header="S12 Touch of Death - Maxroll",
            variant_name="Pit Push",
            filename_parts=(FilenamePart.SOURCE, FilenamePart.BUILD_TITLE, FilenamePart.VARIANT),
        )
        == "maxroll_touch_of_death_pit_push"
    )


def test_import_result_exposes_normalized_profile_and_optional_paragon() -> None:
    result = ImportResult(
        source_name="maxroll", selected_variant="Pit Push", profile=ProfileModel(name="imported profile")
    )

    assert result.profile.name == "imported profile"
    assert result.paragon is None


def test_import_build_passes_one_normalized_request_to_source(monkeypatch) -> None:
    captured: list[ImportRequest] = []

    class FakeSource:
        name = "fixture"

        def fetch_variants(self, request: ImportRequest) -> list[VariantMetadata]:
            return []

        def import_build(self, request: ImportRequest) -> ImportResult:
            captured.append(request)
            return ImportResult(source_name=self.name, selected_variant="Default", profile=ProfileModel(name="profile"))

    monkeypatch.setattr("src.importing.service.select_source", lambda _url: FakeSource())
    result = import_build(
        ImportRequest(url="  https://example.invalid/build\n", options=ImportOptions(custom_file_name="custom.yaml"))
    )

    assert result.source_name == "fixture"
    assert captured[0].url == "https://example.invalid/build"
    assert captured[0].options.custom_file_name == "custom"


def test_select_source_uses_supported_hostname_and_rejects_unknown_urls() -> None:
    assert select_source("https://www.maxroll.gg/d4/planner/example").name == "maxroll"
    assert select_source("https://infinitybuilds.gg/en/builds/example").name == "infinitybuilds"
    assert select_source("https://mobalytics.gg/diablo-4/builds/example").name == "mobalytics"
    try:
        select_source("https://example.invalid/build")
    except UnsupportedImportSourceError:
        pass
    else:
        message = "unsupported URLs must not select a source"
        raise AssertionError(message)


class ImporterWindowStub(QObject):
    import_completed = pyqtSignal()  # ty: ignore[missing-argument]  # PyQt6 stub bug, see #912


class CompletionRecorder(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def record(self) -> None:
        self.calls += 1


def test_create_importer_window_connects_import_completed_callback(monkeypatch) -> None:
    monkeypatch.setattr(importing, "ImporterWindow", ImporterWindowStub)
    recorder = CompletionRecorder()

    window = importing.create_importer_window(on_import_completed=recorder.record)
    window.import_completed.emit()

    assert recorder.calls == 1


def test_create_importer_window_without_callback_still_creates_window(monkeypatch) -> None:
    monkeypatch.setattr(importing, "ImporterWindow", ImporterWindowStub)

    window = importing.create_importer_window()

    assert isinstance(window, ImporterWindowStub)
    window.import_completed.emit()
