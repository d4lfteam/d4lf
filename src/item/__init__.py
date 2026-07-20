"""Public item values, rules, and keep/junk decisions."""

from importlib import import_module
from typing import TYPE_CHECKING

from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import (
    WEAPON_TYPES,
    ItemType,
    is_armor,
    is_consumable,
    is_jewelry,
    is_non_sigil_mapping,
    is_seal_or_charm,
    is_sigil,
    is_socketable,
    is_weapon,
)
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.models import FilterResult, Item, ItemJSONEncoder, MatchedFilter

if TYPE_CHECKING:
    from src.item.data.loader import Dataloader
    from src.item.filter.engine import Filter, ProfileLoadReport
    from src.item.sigil_rules import (
        SIGIL_RULE_TARGET_TYPES,
        SigilItem,
        SigilRules,
        SigilRuleTarget,
        SigilRuleTargetType,
    )

_LAZY_EXPORTS = {
    "Filter": ("src.item.filter.engine", "Filter"),
    "ProfileLoadReport": ("src.item.filter.engine", "ProfileLoadReport"),
    "Dataloader": ("src.item.data.loader", "Dataloader"),
    "SIGIL_RULE_TARGET_TYPES": ("src.item.sigil_rules", "SIGIL_RULE_TARGET_TYPES"),
    "SigilItem": ("src.item.sigil_rules", "SigilItem"),
    "SigilRuleTarget": ("src.item.sigil_rules", "SigilRuleTarget"),
    "SigilRuleTargetType": ("src.item.sigil_rules", "SigilRuleTargetType"),
    "SigilRules": ("src.item.sigil_rules", "SigilRules"),
}

__all__ = [
    "ASPECT_UPGRADES_LABEL",
    "MAX_POWER",
    "SIGIL_RULE_TARGET_TYPES",
    "WEAPON_TYPES",
    "Affix",
    "AffixType",
    "Aspect",
    "Dataloader",
    "Filter",
    "FilterResult",
    "Item",
    "ItemJSONEncoder",
    "ItemRarity",
    "ItemType",
    "MatchedFilter",
    "ProfileLoadReport",
    "SeasonalAttribute",
    "SigilItem",
    "SigilRuleTarget",
    "SigilRuleTargetType",
    "SigilRules",
    "is_armor",
    "is_consumable",
    "is_jewelry",
    "is_non_sigil_mapping",
    "is_seal_or_charm",
    "is_sigil",
    "is_socketable",
    "is_weapon",
]

MAX_POWER = 900
ASPECT_UPGRADES_LABEL = "AspectUpgrades"


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as error:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message) from error
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
