import src.tts
from src.item.data.affix import AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr_tts import read_descr
from src.item.models import Item

LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]


def test_loot_filter_controls_are_not_tts_item_start():
    assert src.tts.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error():
    src.tts.LAST_ITEM = LOOT_FILTER_TTS

    assert read_descr() is None


def test_parser_returns_non_equipment_items_without_image_lookup():
    src.tts.LAST_ITEM = ["GREATER MATERIALS CACHE", "Legendary Cache"]

    assert read_descr() == Item(item_type=ItemType.Cache, original_name="GREATER MATERIALS CACHE")


def test_parser_returns_boss_keys_without_image_lookup():
    src.tts.LAST_ITEM = ["MALIGNANT HEART", "Legendary Boss Key"]

    assert read_descr() == Item(item_type=ItemType.LairBossKey, original_name="MALIGNANT HEART")


def test_unique_helm_with_armory_loadout_has_five_affixes_and_one_aspect():
    src.tts.LAST_ITEM = [
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

    item = read_descr()

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
    src.tts.LAST_ITEM = [
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

    item = read_descr()

    assert item is not None
    assert item.item_type == ItemType.Sigil
    assert item.name == "beast_graveyard"
    assert [affix.name for affix in item.affixes] == ["horadric_strongroom", "hellbound_elites"]
    assert item.rarity == ItemRarity.Rare
