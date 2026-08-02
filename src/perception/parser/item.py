from typing import TYPE_CHECKING

from src.game_data import (
    GameCatalog,
    ItemRarity,
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
from src.item import SeasonalAttribute

if TYPE_CHECKING:
    from src.item import Item

from src.perception.parser.base import _add_affixes_from_tts, _add_sigil_affixes_from_tts, _create_base_item_from_tts
from src.perception.parser.details import _is_codex_upgrade, _is_cosmetic_upgrade


class _TtsItemParser:
    def __init__(self, tts_section: list[str]):
        self.tts_section = tts_section
        self.item: Item | None = None

    def parse(self) -> Item | None:
        if not self.tts_section:
            return None
        if (item := _create_base_item_from_tts(self.tts_section)) is None:
            return None
        self.item = item

        if is_sigil(item.item_type):
            return _add_sigil_affixes_from_tts(self.tts_section, item)
        if item.item_type == ItemType.Cosmetic:
            item.cosmetic_upgrade = True
            return item
        if self._should_return_without_affixes():
            return item
        if not self._is_supported_equipment():
            return None
        if item.rarity == ItemRarity.Mythic and item.is_in_shop:
            return None

        self._validate_unique()
        self._add_upgrade_flags()
        return _add_affixes_from_tts(self.tts_section, item)

    @property
    def _current_item(self) -> Item:
        if self.item is None:
            msg = "TTS parser item has not been initialized"
            raise RuntimeError(msg)
        return self.item

    def _should_return_without_affixes(self) -> bool:
        item = self._current_item
        terminal_item_types = [ItemType.Material, ItemType.Tribute, ItemType.Cache, ItemType.LairBossKey]
        if item.seasonal_attribute == SeasonalAttribute.sanctified:
            return True
        return any([
            is_consumable(item.item_type),
            is_non_sigil_mapping(item.item_type),
            is_socketable(item.item_type),
            item.item_type in terminal_item_types,
        ])

    def _is_supported_equipment(self) -> bool:
        item = self._current_item
        return any([
            is_armor(item.item_type),
            is_jewelry(item.item_type),
            is_weapon(item.item_type),
            is_seal_or_charm(item.item_type),
        ])

    def _validate_unique(self) -> None:
        item = self._current_item
        if item.rarity == ItemRarity.Unique and item.name not in GameCatalog().aspect_unique_dict:
            msg = (
                f"Unrecognized unique {item.name}. This most likely means the name of it reported "
                f"from Diablo 4 is wrong. Please report a bug with this message."
                f" TTS: {self.tts_section}"
            )
            raise IndexError(msg)
        if item.rarity == ItemRarity.Mythic and item.name not in GameCatalog().aspect_unique_dict:
            msg = f"Unrecognized unique {item.name}. This most likely means the name of it reported from Diablo 4 is wrong. Please report a bug with this message. TTS: {self.tts_section}"
            raise IndexError(msg)

    def _add_upgrade_flags(self) -> None:
        item = self._current_item
        item.codex_upgrade = _is_codex_upgrade(self.tts_section)
        item.cosmetic_upgrade = _is_cosmetic_upgrade(self.tts_section)


def parse_item_text(lines: list[str]) -> Item | None:
    return _TtsItemParser(list(lines)).parse()
