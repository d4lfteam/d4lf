from src.config.profile_models import ProfileModel
from src.gui.importer import gui_common
from src.gui.importer.gui_common import _to_yaml_str, build_default_profile_file_name


class _UserDataDir:
    mkdir_called = False
    mkdir_kwargs = {}

    def mkdir(self, **kwargs) -> None:
        self.mkdir_called = True
        self.mkdir_kwargs = kwargs

    def __str__(self) -> str:
        return "browser/mobalytics"


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


def test_to_yaml_str_sorts_aspect_upgrades_and_uses_block_style(mock_ini_loader) -> None:
    profile = ProfileModel(name="test", AspectUpgrades=["snowveiled", "accelerating"])

    yaml_str = _to_yaml_str(profile, exclude_defaults=True, exclude={"name", "Sigils"})

    assert "aspect_upgrades:\n- accelerating\n- snowveiled\n" in yaml_str
    assert "aspect_upgrades: [" not in yaml_str


def test_setup_webdriver_uc_visible_uses_persistent_profile(mocker) -> None:
    driver_cls = mocker.patch.object(gui_common, "Driver")
    user_data_dir = _UserDataDir()

    driver = gui_common.setup_webdriver(uc=True, headless=False, user_data_dir=user_data_dir)

    assert driver == driver_cls.return_value
    assert user_data_dir.mkdir_called
    assert user_data_dir.mkdir_kwargs == {"parents": True, "exist_ok": True}
    driver_cls.assert_called_once_with(uc=True, headed=True, user_data_dir=str(user_data_dir))
