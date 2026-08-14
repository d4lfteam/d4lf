from dataclasses import dataclass

import cv2
import numpy as np

from src.automation.menu import Menu
from src.automation.mouse import Mouse
from src.perception import capture, crop, get_center, search, to_grid, window_to_monitor
from src.settings import get_ui_coordinates


@dataclass
class ItemSlot:
    bounding_box: tuple[int, int, int, int]
    center: tuple[int, int]
    is_fav: bool = False
    is_junk: bool = False


class InventoryBase(Menu):
    """Base class for all menus with a grid inventory.

    Provides methods for identifying occupied and empty slots, item operations, etc.
    """

    def __init__(self, rows: int = 3, columns: int = 11, is_stash: bool = False) -> None:
        super().__init__()
        self.rows = rows
        self.columns = columns
        self.slots_roi = getattr(get_ui_coordinates().roi, f"slots_{self.rows}x{self.columns}")
        if is_stash:
            self.junk_template = "junk_stash"
        else:
            self.junk_template = "junk_inv"

    def get_max_slot_size(self) -> int:
        y_size = int(self.slots_roi[3]) // self.rows
        x_size = int(self.slots_roi[2]) // self.columns
        return max(y_size, x_size)

    def get_item_slots(self, img: np.ndarray | None = None) -> tuple[list[ItemSlot], list[ItemSlot]]:
        """Identifies occupied and empty slots in a grid of slots within a given rectangle of interest (ROI).

        :param roi: The rectangle to consider, represented as (x_min, y_min, width, height).
        :param rows: The number of rows in the grid.
        :param columns: The number of columns in the grid.
        :param img: An optional image (as a numpy array) to use for identifying empty slots.
        :return: Four sets of coordinates.
            - Centers of the occupied slots
            - Centers of the empty slots
        """
        if img is None:
            img = capture()
        slots_roi = (int(self.slots_roi[0]), int(self.slots_roi[1]), int(self.slots_roi[2]), int(self.slots_roi[3]))
        grid = to_grid(slots_roi, self.rows, self.columns)
        occupied_slots = []
        empty_slots = []

        for slot_roi in grid:
            item_slot = ItemSlot(bounding_box=slot_roi, center=get_center(slot_roi))
            slot_img = crop(img, slot_roi)

            hsv_img = cv2.cvtColor(slot_img, cv2.COLOR_BGR2HSV)
            mean_value_overall = np.mean(hsv_img[:, :, 2])
            rel_fav_flag = get_ui_coordinates().roi.rel_fav_flag
            fav_roi = (int(rel_fav_flag[0]), int(rel_fav_flag[1]), int(rel_fav_flag[2]), int(rel_fav_flag[3]))
            fav_flag_crop = crop(hsv_img, fav_roi)
            mean_value_fav = cv2.mean(fav_flag_crop)[2]

            res_junk = search(self.junk_template, slot_img, threshold=0.65, use_grayscale=True)

            if mean_value_fav > 212:
                item_slot.is_fav = True
                occupied_slots.append(item_slot)
            elif res_junk.success and mean_value_overall < 75:
                item_slot.is_junk = True
                occupied_slots.append(item_slot)
            elif mean_value_overall > 37:
                occupied_slots.append(item_slot)
            else:
                empty_slots.append(item_slot)

        return occupied_slots, empty_slots

    def hover_item(self, item: ItemSlot) -> None:
        Mouse.move(*window_to_monitor(item.center), randomize=15)

    # Needed for double checking a TTS
    def hover_left_of_item(self, item: ItemSlot) -> None:
        x, y, width, height = item.bounding_box
        Mouse.move(*window_to_monitor([x - width / 2, y + height / 2]), randomize=15)

    def hover_item_with_delay(self, item: ItemSlot, delay_factor: tuple[float, float] = (2, 3)) -> None:
        Mouse.move(*window_to_monitor(item.center), randomize=15, delay_factor=delay_factor)
