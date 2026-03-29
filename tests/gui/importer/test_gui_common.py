from src.gui.importer.gui_common import build_default_profile_file_name


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

    assert file_name == "d4builds_paladin_s12_robs_cpt_america_pit_push_glasscannon"


def test_build_default_profile_file_name_replaces_stale_season_marker_in_header() -> None:
    file_name = build_default_profile_file_name(
        source_name="maxroll", class_name="Sorcerer", season_number="12", build_header="S11 Crackling Energy Sorc"
    )

    assert file_name == "maxroll_sorcerer_s12_crackling_energy_sorc"
