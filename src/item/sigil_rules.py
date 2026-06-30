from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Literal, Protocol

from src.dataloader import Dataloader
from src.item.data.rarity import ItemRarity

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.item.models import Item

LOGGER = logging.getLogger(__name__)

SigilRuleTargetType = Literal["dungeon", "affix"]
SIGIL_RULE_TARGET_TYPES: tuple[SigilRuleTargetType, ...] = ("dungeon", "affix")


class SigilRuleLike(Protocol):
    name: str
    condition: Sequence[str]


@dataclass(frozen=True, slots=True)
class SigilRuleTarget:
    name: str
    display: str
    target_type: SigilRuleTargetType
    known: bool = True


@dataclass(frozen=True, slots=True)
class SigilItem:
    name: str | None
    rarity: ItemRarity | None
    affix_names: frozenset[str]

    def matches(self, rule: SigilRuleLike) -> bool:
        target_name = rule.name or ""
        if self.name != target_name and target_name not in self.affix_names:
            return False

        conditions = tuple(rule.condition or [])
        return not conditions or any(condition in self.affix_names for condition in conditions)


class SigilRules:
    def __init__(self) -> None:
        sigil_data = Dataloader().affix_sigil_dict_all
        self._targets_by_type: dict[SigilRuleTargetType, tuple[SigilRuleTarget, ...]] = {
            "dungeon": self._build_targets(sigil_data["dungeons"], "dungeon"),
            "affix": self._build_targets(
                {**sigil_data["minor"], **sigil_data["major"], **sigil_data["positive"]}, "affix"
            ),
        }
        self._rarity_map: dict[str, str] = sigil_data["rarities"]
        self._canonical_to_target = {
            (target.target_type, target.name): target
            for targets in self._targets_by_type.values()
            for target in targets
        }
        self._display_to_target = {
            (target.target_type, target.display): target
            for targets in self._targets_by_type.values()
            for target in targets
        }

    @classmethod
    def default(cls) -> SigilRules:
        return _default_sigil_rules()

    def targets(self, target_type: SigilRuleTargetType | None = None) -> tuple[SigilRuleTarget, ...]:
        if target_type is None:
            return self._targets_by_type["dungeon"] + self._targets_by_type["affix"]
        self._validate_target_type(target_type)
        return self._targets_by_type[target_type]

    def target(
        self, value: str, *, target_type: SigilRuleTargetType | None = None, display: bool = False
    ) -> SigilRuleTarget:
        if display:
            return self._target_from_display(value, target_type)
        return self._target_from_canonical(value, target_type)

    def for_item(self, item: Item) -> SigilItem:
        affix_names = tuple(affix.name for affix in item.affixes + item.inherent)
        derived_rarity = self._derive_rarity(affix_names)

        if derived_rarity is None:
            LOGGER.debug(f"Could not resolve sigil rarity from affixes: {list(affix_names)}")

        return SigilItem(name=item.name, rarity=derived_rarity, affix_names=frozenset(affix_names))

    @staticmethod
    def _build_targets(targets: dict[str, str], target_type: SigilRuleTargetType) -> tuple[SigilRuleTarget, ...]:
        return tuple(
            sorted(
                (
                    SigilRuleTarget(name=name, display=display, target_type=target_type)
                    for name, display in targets.items()
                ),
                key=lambda target: target.display.casefold(),
            )
        )

    @staticmethod
    def _validate_target_type(target_type: SigilRuleTargetType) -> None:
        if target_type not in SIGIL_RULE_TARGET_TYPES:
            msg = f"Unknown sigil rule target type: {target_type}"
            raise ValueError(msg)

    def _target_from_canonical(self, value: str, target_type: SigilRuleTargetType | None = None) -> SigilRuleTarget:
        if target_type is not None:
            self._validate_target_type(target_type)
            return self._canonical_to_target.get(
                (target_type, value), SigilRuleTarget(name=value, display=value, target_type=target_type, known=False)
            )

        if target := self._canonical_to_target.get(("dungeon", value)):
            return target
        if target := self._canonical_to_target.get(("affix", value)):
            return target
        return SigilRuleTarget(name=value, display=value, target_type="affix", known=False)

    def _target_from_display(self, value: str, target_type: SigilRuleTargetType | None = None) -> SigilRuleTarget:
        if target_type is not None:
            self._validate_target_type(target_type)
            return self._display_to_target.get(
                (target_type, value), SigilRuleTarget(name=value, display=value, target_type=target_type, known=False)
            )

        if target := self._display_to_target.get(("dungeon", value)):
            return target
        if target := self._display_to_target.get(("affix", value)):
            return target
        return SigilRuleTarget(name=value, display=value, target_type="affix", known=False)

    def _derive_rarity(self, affix_names: Sequence[str]) -> ItemRarity | None:
        for affix_name in affix_names:
            if affix_name in self._rarity_map:
                return ItemRarity(self._rarity_map[affix_name].lower())
        return None


@cache
def _default_sigil_rules() -> SigilRules:
    return SigilRules()
