from typing import TYPE_CHECKING

from src.game_data import GameCatalog

if TYPE_CHECKING:
    from src.game_data import ItemType


def _item_type_summary(item_types: list[ItemType]) -> str:
    if not item_types:
        return "All item types"
    catalog = GameCatalog()
    return ", ".join(catalog.item_type_label(item_type) for item_type in item_types)
