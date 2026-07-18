from src import perception
from src.item import AffixType, Aspect, Item, ItemRarity, ItemType
from src.perception import parse_item_text


def test_equipment_cases_parse_without_item_description_modules(parser_cases):
    for input_item, expected_item in parser_cases:
        assert parse_item_text(input_item) == expected_item


LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]


def test_loot_filter_controls_are_not_tts_item_start():
    assert perception.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    assert parse_item_text(LOOT_FILTER_TTS) is None


def test_parser_returns_non_equipment_items_without_image_lookup():
    item_text = ["GREATER MATERIALS CACHE", "Legendary Cache"]

    assert parse_item_text(item_text) == Item(item_type=ItemType.Cache, original_name="GREATER MATERIALS CACHE")


def test_parser_returns_boss_keys_without_image_lookup():
    item_text = ["MALIGNANT HEART", "Legendary Boss Key"]

    assert parse_item_text(item_text) == Item(item_type=ItemType.LairBossKey, original_name="MALIGNANT HEART")


def test_legendary_horadric_seal_parses_item_power_charm_slots_as_inherent():
    item_text = [
        "SHIELDING HORADRIC SEAL OF ILL-TEMPERANCE",
        "Legendary Horadric Seal",
        "850 Item Power",
        "Unlocks 5 Charm Slots",
        "+11.6% Barrier Generation [8.0 - 12.0]% (+11.6%)",
        "Sescherons Fury:. +9% [8 - 11]% Fury Generation",
        "Berserkers Crucible:. Lucky Hit: Up to a 7% [7 - 9]% chance to Become Berserking",
        "Properties lost when equipped:",
        "Unlocks 1 Charm Slots",
        "18.0%[x] Critical Strike Damage",
        "Seal Power",
        "Seal Power",
        "Requires Level 50. Lord of Hatred Item",
        "Sell Value: 13,386,186 Gold",
        "Right mouse button",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert [(affix.name, affix.text, affix.value, affix.type) for affix in item.inherent] == [
        ("charm_slot", "Unlocks 5 Charm Slots", 5.0, AffixType.inherent)
    ]
    assert [affix.name for affix in item.affixes] == [
        "barrier_generation",
        "sescherons_fury_fury_generation",
        "berserkers_crucible_lucky_hit_up_to_a_chance_to_become_berserking",
    ]


def test_unique_helm_with_armory_loadout_has_five_affixes_and_one_aspect():
    item_text = [
        "GODSLAYER CROWN",
        "Ancestral Unique Helm",
        "900 Item Power",
        "25 ( +25) Quality",
        "Armory Loadout",
        "2,004 Armor",
        "+128 Dexterity +[100 - 121]",
        "+1,754 Maximum Life [1,226 - 1,450]",
        "+35 Maximum Resource [15 - 20]",
        "+1,348 Armor [981 - 1,225]",
        "+3,000 Armor",
        "When you attempt to Incapacitate an enemy, you mark them and all surrounding enemies, pulling them in and dealing 7.5%[x] [7.5 - 10.0]% increased damage to them.",
        "CirMot (300/150) - Lethargic Shadow",
        "Cast 5 Skills then become exhausted for 3 seconds. (1 time). Gain 2 shadows, from the Rogues Dark Shroud Skill, reducing damage taken per shadow. . (Overflow: Gain Multiple Shadows)",
        "The Sahptev faithful believe in a thousand and one gods. If it takes me as many lifetimes, I will find and kill them all.. - Gaspar Stilbian, Veradani Outcast",
        "Requires Level 70. Account Bound. Unique Equipped. Vessel of Hatred Item",
        "Crafted",
        "Sell Value: 114,593 Gold",
        "Durability: 100/100. Tempers: 1/4",
        "Right mouse button",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert [affix.text for affix in item.affixes] == [
        "+128 Dexterity +[100 - 121]",
        "+1,754 Maximum Life [1,226 - 1,450]",
        "+35 Maximum Resource [15 - 20]",
        "+1,348 Armor [981 - 1,225]",
        "+3,000 Armor",
    ]
    assert [(affix.name, affix.value, affix.min_value, affix.max_value, affix.type) for affix in item.affixes] == [
        ("dexterity", 128.0, 100.0, 121.0, AffixType.normal),
        ("maximum_life", 1754.0, 1226.0, 1450.0, AffixType.normal),
        ("maximum_resource", 35.0, 15.0, 20.0, AffixType.normal),
        ("armor", 1348.0, 981.0, 1225.0, AffixType.normal),
        ("armor", 3000.0, None, None, AffixType.greater),
    ]
    assert item.aspect == Aspect(
        name="godslayer_crown",
        min_value=7.5,
        max_value=10.0,
        text="When you attempt to Incapacitate an enemy, you mark them and all surrounding enemies, pulling them in and dealing 7.5%[x] [7.5 - 10.0]% increased damage to them.",
        value=7.5,
    )


def test_sigil_rarity_is_derived_from_tts_affixes():
    item_text = [
        "Nightmare Sigil",
        "Transform this dungeon into. aNightmare Dungeon",
        "Beast Graveyard in Nahantu",
        "DUNGEON AFFIXES",
        "Horadric Strongroom",
        "This place will always contain a Horadric Strongroom.",
        "Hellbound Elites",
        "Elite monsters have the Hellbound affix and deal 20% more damage.",
        "Account Bound. Vessel of Hatred Item",
        "Sell Value: 1 Gold",
        "Right mouse button",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert item.item_type == ItemType.Sigil
    assert item.name == "beast_graveyard"
    assert [affix.name for affix in item.affixes] == ["horadric_strongroom", "hellbound_elites"]
    assert item.rarity == ItemRarity.Rare
