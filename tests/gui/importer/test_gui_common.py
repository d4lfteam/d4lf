from src.config.profile_models import ProfileModel
from src.gui.importer.gui_common import _to_yaml_str, build_default_profile_file_name
from src.gui.importer.importer_config import DEFAULT_FILENAME_PARTS, FilenamePart, ImportConfig


def test_build_default_profile_file_name_maxroll() -> None:
    file_name = build_default_profile_file_name(
        source_name="maxroll", class_name="Spiritborn", build_header="Touch of Death", variant_name="Pit Push"
    )

    assert file_name == "maxroll_spiritborn_touch_of_death_pit_push"


def test_build_default_profile_file_name_d4builds_strips_title_suffix() -> None:
    file_name = build_default_profile_file_name(
        source_name="d4builds", class_name="Barbarian", build_header="Bash Build - D4Builds"
    )

    assert file_name == "d4builds_barbarian_bash_build"


def test_build_default_profile_file_name_d4builds_strips_spaced_title_suffix() -> None:
    file_name = build_default_profile_file_name(
        source_name="d4builds", class_name="Barbarian", build_header="Bash Build · D4 Builds"
    )

    assert file_name == "d4builds_barbarian_bash_build"


def test_build_default_profile_file_name_keeps_unknown_class_and_empty_variant() -> None:
    file_name = build_default_profile_file_name(
        source_name="mobalytics", class_name="Unknown", build_header="Whirlwind Leveling Barb", variant_name=""
    )

    assert file_name == "mobalytics_unknown_whirlwind_leveling_barb"


def test_build_default_profile_file_name_adds_season_and_strips_matching_header_marker() -> None:
    file_name = build_default_profile_file_name(
        source_name="d4builds",
        class_name="Paladin",
        season_number="12",
        build_header="Rob's Cpt. America (S12)",
        variant_name="Pit Push (Glasscannon)",
    )

    assert file_name == "d4builds_s12_paladin_robs_cpt_america_pit_push_glasscannon"


def test_build_default_profile_file_name_replaces_stale_season_marker_in_header() -> None:
    file_name = build_default_profile_file_name(
        source_name="maxroll", class_name="Sorcerer", season_number="12", build_header="S11 Crackling Energy Sorc"
    )

    assert file_name == "maxroll_s12_sorcerer_crackling_energy_sorc"


def test_build_default_profile_file_name_uses_selected_parts() -> None:
    file_name = build_default_profile_file_name(
        source_name="d4builds",
        class_name="Barbarian",
        season_number="12",
        build_header="Bash Build - D4Builds",
        variant_name="Pit Push",
        filename_parts=(FilenamePart.SOURCE, FilenamePart.BUILD_TITLE),
    )

    assert file_name == "d4builds_bash_build"


def test_build_default_profile_file_name_uses_unknown_for_selected_missing_class() -> None:
    file_name = build_default_profile_file_name(source_name="", class_name="", filename_parts=(FilenamePart.CLASS,))

    assert file_name == "unknown"


def test_build_default_profile_file_name_falls_back_when_no_parts_selected() -> None:
    file_name = build_default_profile_file_name(
        source_name="d4builds", class_name="Barbarian", build_header="Bash Build", filename_parts=()
    )

    assert file_name == "imported"


def test_import_config_defaults_to_all_filename_parts() -> None:
    config = ImportConfig(
        url="https://example.invalid",
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=False,
    )

    assert config.filename_parts == DEFAULT_FILENAME_PARTS


def test_import_config_normalizes_filename_parts() -> None:
    config = ImportConfig(
        url="https://example.invalid",
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=False,
        filename_parts=("source", "variant"),
    )

    assert config.filename_parts == (FilenamePart.SOURCE, FilenamePart.VARIANT)


def test_to_yaml_str_sorts_aspect_upgrades_and_uses_block_style(mock_ini_loader) -> None:
    profile = ProfileModel(name="test", AspectUpgrades=["snowveiled", "accelerating"])

    yaml_str = _to_yaml_str(profile, exclude_defaults=True, exclude={"name", "Sigils"})

    assert "aspect_upgrades:\n- accelerating\n- snowveiled\n" in yaml_str
    assert "aspect_upgrades: [" not in yaml_str


def test_to_yaml_str_preserves_paragon_aliases(mock_ini_loader) -> None:
    profile = ProfileModel(
        name="test",
        Paragon={
            "Name": "Build Name",
            "ParagonBoardsList": [
                [{"Name": "Starting Board", "Glyph": "glyph_name", "Rotation": 0, "Nodes": [False] * 441}]
            ],
        },
    )

    yaml_str = _to_yaml_str(profile, exclude_defaults=True, exclude={"name", "Sigils"})

    assert "Paragon:" in yaml_str
    assert "ParagonBoardsList:" in yaml_str
    assert "Name: Build Name" in yaml_str
