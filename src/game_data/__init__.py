"""Localized Diablo 4 game catalog and shared item metadata."""

from src.game_data.catalog import GameCatalog
from src.game_data.item_type import (
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
from src.game_data.rarity import ItemRarity
from src.game_data.sigil_rules import (
    SIGIL_RULE_TARGET_TYPES,
    SigilItem,
    SigilRules,
    SigilRuleTarget,
    SigilRuleTargetType,
)

MAX_POWER = 900

__all__ = [
    "MAX_POWER",
    "SIGIL_RULE_TARGET_TYPES",
    "WEAPON_TYPES",
    "GameCatalog",
    "ItemRarity",
    "ItemType",
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
