from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr.parse_sigil import extract_sigil_name, get_sigil_name_index, parse_sigil_affixes_from_tts
from src.item.models import Item


def _normalize(text: str) -> str:
    return text.lower().replace(" ", "_")


def test_get_sigil_name_index_uses_three_for_escalation_and_bloodied():
    escalation = Item(item_type=ItemType.EscalationSigil)
    bloodied = Item(seasonal_attribute=SeasonalAttribute.bloodied)
    regular = Item(item_type=ItemType.Sigil)

    assert get_sigil_name_index(escalation) == 3
    assert get_sigil_name_index(bloodied) == 3
    assert get_sigil_name_index(regular) == 2


def test_extract_sigil_name_uses_expected_line():
    regular = Item(item_type=ItemType.Sigil)
    escalation = Item(item_type=ItemType.EscalationSigil)

    assert extract_sigil_name(["Nightmare Sigil", "header", "Mercys Reach in Fractured Peaks"], regular, correct_name_func=_normalize) == "mercys_reach"
    assert extract_sigil_name(
        ["Haunted Refuge Escalation Sigil", "header", "ignored", "Haunted Refuge in Hawezar"],
        escalation,
        correct_name_func=_normalize,
    ) == "haunted_refuge"


def test_parse_sigil_affixes_from_tts_uses_affixes_marker_layout():
    item = Item(item_type=ItemType.Sigil, rarity=ItemRarity.Common)
    tts_section = [
        "Nightmare Sigil",
        "Transform this dungeon into a Nightmare Dungeon",
        "Mercys Reach in Fractured Peaks",
        "DUNGEON AFFIXES",
        "Hidden Armory",
        "Exceptional items are kept here, granting elite monsters a powerful loot affix.",
        "Deathly Shadows",
        "Killing a monster has a chance to unleash a volatile pulse after a short delay, dealing heavy area damage.",
        "Account Bound",
    ]

    result = parse_sigil_affixes_from_tts(tts_section, item, correct_name_func=_normalize)

    assert result.name == "mercys_reach"
    assert result.affixes == [
        Affix(name="hidden_armory", type=AffixType.normal),
        Affix(name="deathly_shadows", type=AffixType.normal),
    ]


def test_parse_sigil_affixes_from_tts_falls_back_when_marker_missing():
    item = Item(item_type=ItemType.EscalationSigil, seasonal_attribute=SeasonalAttribute.bloodied)
    tts_section = [
        "Haunted Refuge Escalation Sigil",
        "Legendary Escalation Sigil",
        "Brave a series of dungeons",
        "Haunted Refuge in Hawezar",
        "Hidden Armory",
        "Exceptional items are kept here, granting elite monsters a powerful loot affix.",
        "Deathly Shadows",
        "Killing a monster has a chance to unleash a volatile pulse after a short delay, dealing heavy area damage.",
        "Account Bound",
    ]

    result = parse_sigil_affixes_from_tts(tts_section, item, correct_name_func=_normalize)

    assert result.name == "haunted_refuge"
    assert result.affixes == [
        Affix(name="hidden_armory", type=AffixType.normal),
        Affix(name="deathly_shadows", type=AffixType.normal),
    ]
