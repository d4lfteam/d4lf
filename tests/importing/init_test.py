from src.importing import (
    FilenamePart,
    ImportOptions,
    ImportRequest,
    ImportResult,
    UnsupportedImportSourceError,
    VariantMetadata,
    VariantSelection,
    assemble_profile_file_name,
    import_build,
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


def test_import_build_passes_one_normalized_request_to_source() -> None:
    captured: list[ImportRequest] = []

    class FakeSource:
        name = "fixture"

        def fetch_variants(self, request: ImportRequest) -> list[VariantMetadata]:
            return []

        def import_build(self, request: ImportRequest) -> ImportResult:
            captured.append(request)
            return ImportResult(source_name=self.name, selected_variant="Default", profile=ProfileModel(name="profile"))

    result = import_build(
        ImportRequest(url="  https://example.invalid/build\n", options=ImportOptions(custom_file_name="custom.yaml")),
        source=FakeSource(),
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
