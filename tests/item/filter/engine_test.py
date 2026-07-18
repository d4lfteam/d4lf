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

from .conftest import _create_mocked_filter, filters

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
