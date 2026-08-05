import logging

from src.game_data import SIGIL_RULE_TARGET_TYPES, ItemRarity, SigilRules
from src.item import Item
from src.item.data.affix import Affix
from src.profiles import SigilConditionModel


def test_target_types_preserve_editor_choices():
    assert SIGIL_RULE_TARGET_TYPES == ("dungeon", "affix")


def test_target_derives_affix_and_round_trips_display():
    rules = SigilRules.default()
    target = rules.target("amethyst_reserve")
    assert rules.target(target.display, target_type="affix", display=True).name == "amethyst_reserve"


def test_target_derives_dungeon():
    rules = SigilRules.default()
    assert rules.target(rules.targets("dungeon")[0].name).target_type == "dungeon"


def test_unknown_target_stays_loose():
    target = SigilRules.default().target("unknown_sigil_rule_target")
    assert target.known is False
    assert target.target_type == "affix"


def test_for_item_derives_rarity_from_affixes():
    assert SigilRules.default().for_item(Item(affixes=[Affix(name="amethyst_reserve")])).rarity == ItemRarity.Rare


def test_for_item_unknown_rarity_logs_debug(caplog):
    with caplog.at_level(logging.DEBUG, logger="src.game_data.sigil_rules"):
        sigil_item = SigilRules.default().for_item(Item(affixes=[Affix(name="shadow_damage")]))
    assert sigil_item.rarity is None
    assert any("Could not resolve sigil rarity" in record.message for record in caplog.records)


def test_sigil_item_matches_rule_target_and_condition():
    item = Item(name="jalals_vigil", affixes=[Affix(name="shadow_damage")], inherent=[Affix(name="iron_hold")])
    sigil_item = SigilRules.default().for_item(item)
    assert sigil_item.matches(SigilConditionModel(name="jalals_vigil", condition=[]))
    assert sigil_item.matches(SigilConditionModel(name="iron_hold", condition=["shadow_damage"]))
    assert not sigil_item.matches(SigilConditionModel(name="iron_hold", condition=["amethyst_reserve"]))
