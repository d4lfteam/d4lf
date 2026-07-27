import typing

import pytest

from src.item import Affix, AffixType, Item, ItemRarity, ItemType
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    ItemFilterModel,
    ParagonPayloadModel,
    ProfileDocumentStore,
    ProfileModel,
)
from src.settings import Settings

from .conftest import _create_mocked_filter, _patch_override_settings, filters, sigil_jalal, sigil_mythic_fallback

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("rarity", "expected"),
    [
        (ItemRarity.Rare, {"rarity_test.RareOnly", "rarity_test.AnyRarity"}),
        (ItemRarity.Legendary, {"rarity_test.AnyRarity"}),
    ],
)
def test_affix_rarity_gate(rarity: ItemRarity, expected: set[str], mocker: MockerFixture):
    boots = Item(
        item_type=ItemType.Boots,
        power=900,
        rarity=rarity,
        affixes=[Affix(name="movement_speed", value=10)],
        inherent=[],
    )
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.affix_rarity.name: filters.affix_rarity.affixes}
    assert {m.profile for m in test_filter.should_keep(boots).matched} == expected


def test_duplicate_affix_requirements_match_distinct_item_rows(mocker: MockerFixture):
    profile = ProfileModel(
        name="duplicates",
        affixes=[
            {
                "TwoArmor": ItemFilterModel(
                    item_type=[ItemType.Helm],
                    affix_pool=[
                        AffixFilterCountModel(count=[AffixFilterModel(name="armor"), AffixFilterModel(name="armor")])
                    ],
                )
            }
        ],
    )
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {profile.name: profile.affixes}

    one_armor = Item(
        item_type=ItemType.Helm, power=900, rarity=ItemRarity.Rare, affixes=[Affix(name="armor", value=100)]
    )
    assert not test_filter.should_keep(one_armor).keep

    first_armor = Affix(name="armor", value=100)
    second_armor = Affix(name="armor", value=200)
    two_armors = Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Rare, affixes=[first_armor, second_armor])
    result = test_filter.should_keep(two_armors)

    assert result.keep
    assert result.matched[0].matched_affixes == [first_armor, second_armor]
    assert result.matched[0].matched_affixes[0] is first_armor
    assert result.matched[0].matched_affixes[1] is second_armor


def test_duplicate_affix_requirements_assign_value_and_greater_constraints(mocker: MockerFixture):
    profile = ProfileModel(
        name="duplicates",
        affixes=[
            {
                "TwoArmor": ItemFilterModel(
                    item_type=[ItemType.Helm],
                    min_greater_affix_count=1,
                    affix_pool=[
                        AffixFilterCountModel(
                            count=[
                                AffixFilterModel(name="armor"),
                                AffixFilterModel(name="armor", value=200, want_greater=True),
                            ]
                        )
                    ],
                )
            }
        ],
    )
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {profile.name: profile.affixes}

    first_armor = Affix(name="armor", value=100)
    second_armor = Affix(name="armor", value=200, type=AffixType.greater)
    item = Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Rare, affixes=[first_armor, second_armor])

    result = test_filter.should_keep(item)

    assert result.keep
    assert result.matched[0].matched_affixes == [first_armor, second_armor]
    assert result.matched[0].matched_affixes[1] is second_armor


def test_filter_loads_typed_paragon_payload(tmp_path, mocker: MockerFixture) -> None:
    settings = mocker.Mock(spec=Settings)
    settings.user_dir = tmp_path
    settings.general.profiles = ["typed_paragon"]
    mocker.patch("src.item.filter.engine.get_settings", return_value=settings)

    profile = ProfileModel(
        name="typed_paragon",
        Paragon={
            "Name": "Build Name",
            "ParagonBoardsList": [
                [{"Name": "Starting Board", "Glyph": "glyph_name", "Rotation": 0, "Nodes": [False] * 441}]
            ],
        },
    )
    ProfileDocumentStore(profiles_dir=tmp_path / "profiles", full_dump=False).save_new(
        file_name="typed_paragon", profile=profile, source="https://example.invalid"
    )

    test_filter = _create_mocked_filter(mocker)
    test_filter.files_loaded = False
    test_filter.load_files()

    assert isinstance(test_filter.get_paragon_filters()["typed_paragon"], ParagonPayloadModel)


def test_filter_skips_invalid_profile_but_keeps_valid_profiles(tmp_path, mocker: MockerFixture) -> None:
    settings = mocker.Mock(spec=Settings)
    settings.user_dir = tmp_path
    settings.general.profiles = ["good", "bad"]
    mocker.patch("src.item.filter.engine.get_settings", return_value=settings)
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "good.yaml").write_text("{}\n", encoding="utf-8")
    (profile_dir / "bad.yaml").write_text("[invalid", encoding="utf-8")

    test_filter = _create_mocked_filter(mocker)
    test_filter.files_loaded = False
    test_filter.load_files()

    assert "good" in test_filter.affix_filters or test_filter.files_loaded
    assert "bad" not in test_filter.affix_filters
    assert test_filter.load_failures == ("bad",)


def test_filter_removes_profile_only_after_second_missing_check(tmp_path, mocker: MockerFixture) -> None:
    settings = mocker.Mock(spec=Settings)
    settings.user_dir = tmp_path
    settings.general.profiles = ["missing"]
    mocker.patch("src.item.filter.engine.get_settings", return_value=settings)
    (tmp_path / "profiles").mkdir()
    test_filter = _create_mocked_filter(mocker)

    test_filter.files_loaded = False
    test_filter.load_files()
    settings.save_value.assert_not_called()
    test_filter.load_files()
    settings.save_value.assert_called_once_with("general", "profiles", "")


def test_invalid_profile_edit_emits_one_report_per_file_version(tmp_path, mocker: MockerFixture) -> None:
    settings = mocker.Mock(spec=Settings)
    settings.user_dir = tmp_path
    settings.general.profiles = ["bad"]
    mocker.patch("src.item.filter.engine.get_settings", return_value=settings)
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    profile_path = profile_dir / "bad.yaml"
    profile_path.write_text("[invalid", encoding="utf-8")
    test_filter = _create_mocked_filter(mocker)
    reports = []
    test_filter.register_profile_failure_listener(reports.append)

    test_filter.files_loaded = False
    test_filter.load_files()
    test_filter.load_files()
    profile_path.write_text("[still-invalid", encoding="utf-8")
    test_filter.load_files()

    assert len(reports) == 2


CASES = (
    (
        "filter_equipment",
        Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Rare),
        False,
        Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Mythic),
    ),
    ("filter_sigils", sigil_jalal, True, sigil_mythic_fallback),
    (
        "filter_tributes",
        Item(name="tribute_of_harmony", rarity=ItemRarity.Magic, item_type=ItemType.Tribute),
        True,
        Item(name="tribute_of_harmony", rarity=ItemRarity.Mythic, item_type=ItemType.Tribute),
    ),
    (
        "filter_seals",
        Item(name="seal", rarity=ItemRarity.Rare, item_type=ItemType.HoradricSeal),
        False,
        Item(name="seal", rarity=ItemRarity.Mythic, item_type=ItemType.HoradricSeal),
    ),
    (
        "filter_charms",
        Item(name="charm", rarity=ItemRarity.Rare, item_type=ItemType.Charm),
        False,
        Item(name="charm", rarity=ItemRarity.Mythic, item_type=ItemType.Charm),
    ),
)


@pytest.mark.parametrize(("setting", "item", "enabled_keep", "mythic"), CASES)
def test_filterable_item_category_override_skips_all_items_when_disabled(setting, item, enabled_keep, mythic, mocker):
    settings = _patch_override_settings(mocker, **{setting: False})
    test_filter = _create_mocked_filter(mocker)

    skipped = test_filter.should_keep(item)

    assert skipped.skipped
    assert not skipped.keep
    assert skipped.matched == []

    setattr(settings.general, setting, True)
    enabled = test_filter.should_keep(item)

    assert not enabled.skipped
    assert enabled.keep is enabled_keep

    setattr(settings.general, setting, False)
    mythic_result = test_filter.should_keep(mythic)

    assert mythic_result.skipped
    assert not mythic_result.keep
    assert mythic_result.matched == []

    setattr(settings.general, setting, True)
    enabled_mythic = test_filter.should_keep(mythic)

    assert not enabled_mythic.skipped
    assert enabled_mythic.keep


def test_disabled_sigils_skip_escalation_before_sigil_behavior(mocker):
    _patch_override_settings(mocker, filter_sigils=False, ignore_escalation_sigils=False)
    test_filter = _create_mocked_filter(mocker)
    escalation_sigil = Item(item_type=ItemType.EscalationSigil, name="escalation")

    result = test_filter.should_keep(escalation_sigil)

    assert result.skipped
    assert result.matched == []


def test_disabled_category_still_loads_and_reports_invalid_profiles(tmp_path, mocker):
    settings = _patch_override_settings(mocker, filter_equipment=False)
    settings.general.profiles = ["invalid"]
    settings.user_dir = tmp_path
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "invalid.yaml").write_text("[invalid", encoding="utf-8")
    test_filter = _create_mocked_filter(mocker)
    test_filter.files_loaded = False

    result = test_filter.should_keep(Item(item_type=ItemType.Helm, power=900, rarity=ItemRarity.Rare))

    assert result.skipped
    assert test_filter.load_failures == ("invalid",)
