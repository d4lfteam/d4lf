from src.gui.importer.gui_common import build_default_profile_file_name


def test_build_default_profile_file_name_maxroll() -> None:
    file_name = build_default_profile_file_name(
        url="https://maxroll.gg/d4/build-guides/example",
        class_name="Spiritborn",
        build_header="Touch of Death",
        variant_name="Pit Push",
    )

    assert file_name == "maxroll_spiritborn_touch_of_death_pit_push"


def test_build_default_profile_file_name_d4builds_strips_title_suffix() -> None:
    file_name = build_default_profile_file_name(
        url="https://d4builds.gg/builds/example",
        class_name="Barbarian",
        build_header="Bash Build - D4Builds",
    )

    assert file_name == "d4builds_barbarian_bash_build"


def test_build_default_profile_file_name_d4builds_strips_spaced_title_suffix() -> None:
    file_name = build_default_profile_file_name(
        url="https://d4builds.gg/builds/example",
        class_name="Barbarian",
        build_header="Bash Build · D4 Builds",
    )

    assert file_name == "d4builds_barbarian_bash_build"


def test_build_default_profile_file_name_skips_unknown_class_and_empty_variant() -> None:
    file_name = build_default_profile_file_name(
        url="https://mobalytics.gg/diablo-4/builds/example",
        class_name="Unknown",
        build_header="Whirlwind Leveling Barb",
        variant_name="",
    )

    assert file_name == "mobalytics_whirlwind_leveling_barb"
