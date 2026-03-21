import lxml.html

from src.gui.importer.d4builds import _build_default_file_name as build_d4builds_default_file_name
from src.gui.importer.gui_common import build_default_profile_name, sanitize_profile_file_name
from src.gui.importer.maxroll import _build_default_file_name as build_maxroll_default_file_name
from src.gui.importer.mobalytics import _build_default_file_name as build_mobalytics_default_file_name


def test_build_default_profile_name_deduplicates_case_insensitively():
    assert build_default_profile_name("maxroll", "My Build", "my build", "Speed Farm") == "maxroll_My Build_Speed Farm"


def test_sanitize_profile_file_name_preserves_hyphen_separator():
    assert (
        sanitize_profile_file_name("d4builds_Pulverize S12 Endgame_Tower Push - BIS")
        == "d4builds_Pulverize_S12_Endgame_Tower_Push_-_BIS"
    )


def test_d4builds_default_file_name_uses_build_and_variant_labels():
    data = lxml.html.fromstring('<h2 class="builder__header__description">Pulverize S12 Endgame</h2>')

    assert (
        build_d4builds_default_file_name(
            data=data,
            class_name="Druid",
            source_url="https://d4builds.gg/builds/pulverize-druid-endgame/?var=0",
            selected_variant_parts=["Tower Push - BIS"],
        )
        == "d4builds_Pulverize S12 Endgame_Tower Push - BIS"
    )


def test_maxroll_default_file_name_uses_source_build_variant():
    assert (
        build_maxroll_default_file_name(
            all_data={"class": "Paladin", "name": "Blessed Shield Endgame"},
            active_profile={"name": "Speed Farm", "items": {"weapon": 1}},
            build_id=0,
        )
        == "maxroll_Blessed Shield Endgame_Speed Farm"
    )


def test_mobalytics_default_file_name_uses_source_build_variant():
    assert (
        build_mobalytics_default_file_name(
            build_name="Pulverize Endgame",
            class_name="druid",
            variant_name="Speed Farm",
            variant_id="123",
        )
        == "mobalytics_Pulverize Endgame_Speed Farm"
    )
