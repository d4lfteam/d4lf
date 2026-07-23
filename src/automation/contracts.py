from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np

    from src.automation.inventory import ItemSlot


class Inventory(Protocol):
    menu_name: str

    def open(self) -> bool: ...

    def is_open(self, img: np.ndarray | None = None) -> bool: ...

    def get_item_slots(self, img: np.ndarray | None = None) -> tuple[list[ItemSlot], list[ItemSlot]]: ...

    def get_max_slot_size(self) -> int: ...

    def hover_item(self, item: ItemSlot) -> None: ...

    def hover_item_with_delay(self, item: ItemSlot, delay_factor: tuple[float, float] = (2, 3)) -> None: ...


class StashInventory(Inventory, Protocol):
    def switch_to_tab(self, tab_idx: int) -> bool: ...
