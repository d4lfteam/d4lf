from __future__ import annotations

import typing

import pytest
from natsort import natsorted

from src.config.loader import IniConfigLoader
from src.config.profile_models import (
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicSealFilterModel,
    SealFilterModel,
    SigilPriority,
)
from src.config.settings_models import AspectFilterType
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.filter import Filter, FilterResult
from src.item.models import Item
from tests.item.filter.data import filters
from tests.item.filter.data.affixes import affixes
from tests.item.filter.data.aspects import aspects
from tests.item.filter.data.sigils import sigil_jalal, sigil_priority, sigils
from tests.item.filter.data.tributes import tributes
from tests.item.filter.data.uniques import global_uniques, simple_mythics, uniques_with_affixes

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _create_mocked_filter(mocker: MockerFixture) -> Filter:
    filter_obj = Filter()
    # Filter is singleton so we need to reset the filters to be safe
    filter_obj.affix_filters = {}
    filter_obj.aspect_upgrade_filters = {}
    filter_obj.paragon_filters = {}
    filter_obj.global_unique_filters = {}
    filter_obj.seal_filters = {}
    filter_obj.charm_filters = {}
    filter_obj.sigil_filters = {}
    filter_obj.tribute_filters = {}
    filter_obj.files_loaded = True
    mocker.patch.object(filter_obj, "_did_files_change", return_value=False)
    return filter_obj


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(affixes), ids=[name for name, _, _ in natsorted(affixes)]
)
def test_affixes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.affix.name: filters.affix.affixes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(aspects), ids=[name for name, _, _ in natsorted(aspects)]
)
def test_aspects(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    general_mock = mocker.patch.object(IniConfigLoader(), "_general")
    general_mock.keep_aspects = AspectFilterType.upgrade
    mocker.patch.object(test_filter, "_check_affixes", return_value=FilterResult(keep=False, matched=[]))
    test_filter.aspect_upgrade_filters = {filters.aspects_filters.name: filters.aspects_filters.aspect_upgrades}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(global_uniques), ids=[name for name, _, _ in natsorted(global_uniques)]
)
def test_global_uniques(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.global_unique_filters = {filters.global_unique.name: filters.global_unique.global_uniques}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(("_name", "result", "item"), natsorted(sigils), ids=[name for name, _, _ in natsorted(sigils)])
def test_sigils(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil.name: filters.sigil.sigils}
    assert natsorted([match.profile.split(".")[0] for match in test_filter.should_keep(item).matched]) == natsorted(
        result
    )


def test_sigil_empty_lists(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_whitelist_only.name: filters.sigil_whitelist_only.sigils}
    assert test_filter.should_keep(sigil_jalal).matched == []
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_whitelist_only.name
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_blacklist_only.name: filters.sigil_blacklist_only.sigils}
    assert test_filter.should_keep(sigil_jalal).matched[0].profile == filters.sigil_blacklist_only.name
    assert test_filter.should_keep(sigil_priority).matched == []


def test_sigil_priority(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.sigil_filters = {filters.sigil_priority.name: filters.sigil_priority.sigils}
    assert test_filter.should_keep(sigil_priority).matched == []
    test_filter.sigil_filters[next(iter(test_filter.sigil_filters))].priority = SigilPriority.whitelist
    assert test_filter.should_keep(sigil_priority).matched[0].profile == filters.sigil_priority.name


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(tributes), ids=[name for name, _, _ in natsorted(tributes)]
)
def test_tributes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.tribute_filters = {filters.tributes.name: filters.tributes.tributes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("item", "filter_attr", "section_name", "filter_model", "dynamic_model"),
    [
        (
            Item(
                item_type=ItemType.HoradricSeal,
                name="unimportant_seal_name",
                rarity=ItemRarity.Legendary,
                affixes=[Affix(name="cooldown_reduction")],
            ),
            "seal_filters",
            "Seals",
            SealFilterModel,
            DynamicSealFilterModel,
        ),
        (
            Item(
                item_type=ItemType.Charm,
                name="unimportant_charm_name",
                rarity=ItemRarity.Rare,
                affixes=[Affix(name="maximum_life")],
            ),
            "charm_filters",
            "Charms",
            CharmFilterModel,
            DynamicCharmFilterModel,
        ),
    ],
)
def test_seal_or_charm_sections(
    item: Item, filter_attr: str, section_name: str, filter_model, dynamic_model, mocker: MockerFixture
):
    test_filter = _create_mocked_filter(mocker)
    spellcraft_filter = filter_model(affix_pool=[{"count": [item.affixes[0].name]}], rarities=[item.rarity])
    setattr(test_filter, filter_attr, {"spellcraft": [dynamic_model(root={"wanted": spellcraft_filter})]})

    match = test_filter.should_keep(item).matched[0]
    assert match.profile == f"spellcraft.{section_name}.wanted"
    assert match.matched_affixes == item.affixes


def test_charm_filter_matches_set_name(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    item = Item(
        item_type=ItemType.Charm,
        name="linta_of_the_frozen_sea",
        rarity=ItemRarity.Legendary,
        set_name="breath_of_the_frozen_sea",
        affixes=[Affix(name="potion_healing")],
    )
    charm_filter = CharmFilterModel(set="Breath of the Frozen Sea")
    test_filter.charm_filters = {"spellcraft": [DynamicCharmFilterModel(root={"wanted": charm_filter})]}

    match = test_filter.should_keep(item).matched[0]

    assert match.profile == "spellcraft.Charms.wanted"


def test_charm_filter_matches_unique_aspect_name(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    item = Item(
        item_type=ItemType.Charm,
        name="linta_of_the_frozen_sea",
        rarity=ItemRarity.Legendary,
        set_name="breath_of_the_frozen_sea",
        affixes=[Affix(name="potion_healing")],
    )
    charm_filter = CharmFilterModel(uniqueAspect="Linta of the Frozen Sea")
    test_filter.charm_filters = {"spellcraft": [DynamicCharmFilterModel(root={"wanted": charm_filter})]}

    match = test_filter.should_keep(item).matched[0]

    assert match.profile == "spellcraft.Charms.wanted"


def test_charm_filter_rejects_wrong_set_or_unique_aspect(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    item = Item(
        item_type=ItemType.Charm,
        name="linta_of_the_frozen_sea",
        rarity=ItemRarity.Legendary,
        set_name="breath_of_the_frozen_sea",
        affixes=[Affix(name="potion_healing")],
    )
    charm_filter = CharmFilterModel(set="applied_alchemy", uniqueAspect="another_charm")
    test_filter.charm_filters = {"spellcraft": [DynamicCharmFilterModel(root={"wrong": charm_filter})]}

    assert test_filter.should_keep(item).matched == []


def test_seal_filter_matches_slot_count(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    item = Item(
        item_type=ItemType.HoradricSeal,
        name="unimportant_seal_name",
        rarity=ItemRarity.Legendary,
        affixes=[Affix(name="cooldown_reduction"), Affix(name="maximum_life")],
    )
    seal_filter = SealFilterModel(slotCount=2)
    test_filter.seal_filters = {"spellcraft": [DynamicSealFilterModel(root={"wanted": seal_filter})]}

    match = test_filter.should_keep(item).matched[0]

    assert match.profile == "spellcraft.Seals.wanted"


def test_seal_filter_rejects_wrong_slot_count(mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    item = Item(
        item_type=ItemType.HoradricSeal,
        name="unimportant_seal_name",
        rarity=ItemRarity.Legendary,
        affixes=[Affix(name="cooldown_reduction"), Affix(name="maximum_life")],
    )
    seal_filter = SealFilterModel(slotCount=3)
    test_filter.seal_filters = {"spellcraft": [DynamicSealFilterModel(root={"wrong": seal_filter})]}

    assert test_filter.should_keep(item).matched == []


@pytest.mark.parametrize(
    ("item", "filter_attr", "filter_model", "dynamic_model"),
    [
        (
            Item(
                item_type=ItemType.HoradricSeal,
                rarity=ItemRarity.Mythic,
                affixes=[Affix(name="cooldown_reduction", type=AffixType.greater)],
            ),
            "seal_filters",
            SealFilterModel,
            DynamicSealFilterModel,
        ),
        (
            Item(
                item_type=ItemType.Charm,
                rarity=ItemRarity.Mythic,
                affixes=[Affix(name="maximum_life", type=AffixType.greater)],
            ),
            "charm_filters",
            CharmFilterModel,
            DynamicCharmFilterModel,
        ),
    ],
)
def test_mythic_seal_or_charm_always_kept(
    item: Item, filter_attr: str, filter_model, dynamic_model, mocker: MockerFixture
):
    test_filter = _create_mocked_filter(mocker)
    spellcraft_filter = filter_model(affix_pool=[{"count": ["movement_speed"]}], rarities=[ItemRarity.Common])
    setattr(test_filter, filter_attr, {"spellcraft": [dynamic_model(root={"wrong": spellcraft_filter})]})

    assert test_filter.should_keep(item).keep
    assert test_filter.should_keep(item).matched[0].profile.startswith("Mythic")


@pytest.mark.parametrize(
    ("_name", "result", "item"),
    natsorted(uniques_with_affixes),
    ids=[name for name, _, _ in natsorted(uniques_with_affixes)],
)
def test_uniques_with_affixes(_name: str, result: list[str], item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {filters.unique_affixes.name: filters.unique_affixes.affixes}
    assert natsorted([match.profile for match in test_filter.should_keep(item).matched]) == natsorted(result)


@pytest.mark.parametrize(
    ("_name", "result", "item"), natsorted(simple_mythics), ids=[name for name, _, _ in natsorted(simple_mythics)]
)
def test_mythic_always_kept(_name: str, result: bool, item: Item, mocker: MockerFixture):
    test_filter = _create_mocked_filter(mocker)
    test_filter.global_unique_filters = {filters.always_keep_mythics.name: filters.always_keep_mythics.global_uniques}
    assert test_filter.should_keep(item).keep == result
