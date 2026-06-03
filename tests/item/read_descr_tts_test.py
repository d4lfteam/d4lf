import numpy as np

import src.tts
from src.config.ui import ResManager
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import _add_affixes_from_tts_mixed, read_descr
from src.item.models import Item
from src.template_finder import TemplateMatch

LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]


def test_loot_filter_controls_are_not_tts_item_start():
    assert src.tts.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    src.tts.LAST_ITEM = LOOT_FILTER_TTS

    assert read_descr() is None


def test_seal_boosted_set_locations_fall_back_to_line_offsets():
    ResManager().set_resolution("3840x2160")
    item = Item(
        item_type=ItemType.HoradricSeal,
        name="efficient_horadric_seal_of_fervor",
        original_name="EFFICIENT HORADRIC SEAL OF FERVOR",
        rarity=ItemRarity.Legendary,
    )
    tts_section = [
        "EFFICIENT HORADRIC SEAL OF FERVOR",
        "Legendary Horadric Seal",
        "Unlocks 5 Charm Slots",
        "7.5% Resource Cost Reduction [7.5]",
        "Habacalva's Cauldron:",
        "+255 Life On Hit",
        "Tal Rasha's Threefold Way:",
        "+2 to Ball Lightning",
        "Right mouse button",
    ]
    affix_bullets = [
        TemplateMatch(center=(50, 100), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 150), name="affix_bullet_point_1"),
    ]

    result = _add_affixes_from_tts_mixed(tts_section, item, affix_bullets, np.zeros((1, 1, 3)), aspect_bullet=None)

    assert result.charm_slots_loc == (50, 100)
    assert result.affixes[0].loc == (50, 150)
    assert [
        (boosted_set.name, boosted_set.loc, boosted_set.affix.loc if boosted_set.affix else None)
        for boosted_set in result.boosted_sets
    ] == [("habacalvas_cauldron", (50, 200), None), ("tal_rashas_threefold_way", (50, 300), None)]


def test_seal_boosted_affix_locations_do_not_consume_set_bullets():
    ResManager().set_resolution("3840x2160")
    item = Item(
        item_type=ItemType.HoradricSeal,
        name="efficient_horadric_seal_of_fervor",
        original_name="EFFICIENT HORADRIC SEAL OF FERVOR",
        rarity=ItemRarity.Legendary,
    )
    tts_section = [
        "EFFICIENT HORADRIC SEAL OF FERVOR",
        "Legendary Horadric Seal",
        "Unlocks 5 Charm Slots",
        "7.5% Resource Cost Reduction [7.5]",
        "Habacalva's Cauldron:",
        "+255 Life On Hit",
        "Tal Rasha's Threefold Way:",
        "+2 to Ball Lightning",
        "Right mouse button",
    ]
    affix_bullets = [
        TemplateMatch(center=(50, 100), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 150), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 200), name="boosted_bullet_point"),
        TemplateMatch(center=(50, 300), name="boosted_bullet_point"),
    ]

    result = _add_affixes_from_tts_mixed(tts_section, item, affix_bullets, np.zeros((1, 1, 3)), aspect_bullet=None)

    assert [
        (boosted_set.name, boosted_set.loc, boosted_set.affix.loc if boosted_set.affix else None)
        for boosted_set in result.boosted_sets
    ] == [("habacalvas_cauldron", (50, 200), None), ("tal_rashas_threefold_way", (50, 300), None)]


def test_seal_boosted_set_locations_skip_affix_line_false_matches():
    ResManager().set_resolution("3840x2160")
    item = Item(
        item_type=ItemType.HoradricSeal,
        name="efficient_horadric_seal_of_fervor",
        original_name="EFFICIENT HORADRIC SEAL OF FERVOR",
        rarity=ItemRarity.Legendary,
    )
    tts_section = [
        "EFFICIENT HORADRIC SEAL OF FERVOR",
        "Legendary Horadric Seal",
        "Unlocks 5 Charm Slots",
        "7.5% Resource Cost Reduction [7.5]",
        "Habacalva's Cauldron:",
        "+255 Life On Hit",
        "Tal Rasha's Threefold Way:",
        "+2 to Ball Lightning",
        "Right mouse button",
    ]
    affix_bullets = [
        TemplateMatch(center=(50, 100), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 150), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 200), name="boosted_bullet_point"),
        TemplateMatch(center=(50, 250), name="boosted_bullet_point"),
        TemplateMatch(center=(50, 300), name="boosted_bullet_point"),
    ]

    result = _add_affixes_from_tts_mixed(tts_section, item, affix_bullets, np.zeros((1, 1, 3)), aspect_bullet=None)

    assert [(boosted_set.name, boosted_set.loc) for boosted_set in result.boosted_sets] == [
        ("habacalvas_cauldron", (50, 200)),
        ("tal_rashas_threefold_way", (50, 300)),
    ]


def test_seal_boosted_set_locations_use_actual_second_set_bullet():
    ResManager().set_resolution("3840x2160")
    item = Item(
        item_type=ItemType.HoradricSeal,
        name="efficient_horadric_seal_of_fervor",
        original_name="EFFICIENT HORADRIC SEAL OF FERVOR",
        rarity=ItemRarity.Legendary,
    )
    tts_section = [
        "EFFICIENT HORADRIC SEAL OF FERVOR",
        "Legendary Horadric Seal",
        "Unlocks 5 Charm Slots",
        "7.5% Resource Cost Reduction [7.5]",
        "Habacalva's Cauldron:",
        "+255 Life On Hit",
        "Tal Rasha's Threefold Way:",
        "+2 to Ball Lightning",
        "Right mouse button",
    ]
    affix_bullets = [
        TemplateMatch(center=(50, 100), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 150), name="affix_bullet_point_1"),
        TemplateMatch(center=(50, 200), name="boosted_bullet_point"),
        TemplateMatch(center=(50, 250), name="boosted_bullet_point"),
        TemplateMatch(center=(50, 275), name="boosted_bullet_point"),
    ]

    result = _add_affixes_from_tts_mixed(tts_section, item, affix_bullets, np.zeros((1, 1, 3)), aspect_bullet=None)

    assert [(boosted_set.name, boosted_set.loc) for boosted_set in result.boosted_sets] == [
        ("habacalvas_cauldron", (50, 200)),
        ("tal_rashas_threefold_way", (50, 275)),
    ]
