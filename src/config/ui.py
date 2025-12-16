import logging

import cv2
import numpy as np

from src.config.data import POSITIONS, Template, load_templates
from src.config.helper import singleton
from src.config.models import UiOffsetsModel, UiPosModel, UiRoiModel

LOGGER = logging.getLogger("d4lf")


class _ResTransformer:
    def __init__(self, resolution: str):
        self._target_width, self._target_height = map(int, resolution.split("x"))
        self._scale_x = self._target_width / POSITIONS[0][0]
        self._scale_y = self._target_height / POSITIONS[0][1]
        self._highest_ratio = 27 / 9

    def _resize_image(self, src: np.ndarray) -> np.ndarray:
        height, width = src.shape[:2]
        return cv2.resize(src=src, dsize=(int(width * self._scale_y), int(height * self._scale_y)))

    def _transform(self, value: int) -> int:
        return int(value * self._scale_y)

    def _transform_array(self, value: np.ndarray, scale_only=False) -> np.ndarray:
        new_value = value * self._scale_y
        if scale_only:
            return new_value.astype(int)

        # handle widescreen stretching
        width_org = int(self._scale_y * POSITIONS[0][0])
        is_right_side = new_value[0] > width_org / 2
        if is_right_side:
            new_value[0] += self._target_width - width_org

        # handle black bars
        aspect_ratio = self._target_width / self._target_height
        if aspect_ratio > self._highest_ratio:
            new_width = int(self._target_height * self._highest_ratio)
            black_bar = (self._target_width - new_width) // 2
            new_value[0] = new_value[0] - black_bar if is_right_side else new_value[0] + black_bar

        return new_value.astype(int)

    def _transform_list_of_tuples(self, value: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [self._transform_tuples(value=v) for v in value]

    def _transform_templates(self, templates: dict[str, Template]) -> dict[str, Template]:
        result = {}
        for key, value in templates.items():
            if key.endswith("_special"):  # do not transform templates that end with _special
                result[key] = value
            else:
                result[key] = Template(
                    name=value.name,
                    img_bgra=self._resize_image(src=value.img_bgra),
                    img_bgr=self._resize_image(src=value.img_bgr),
                    img_gray=self._resize_image(src=value.img_gray),
                    alpha_mask=self._resize_image(src=value.alpha_mask) if value.alpha_mask is not None else None,
                )
        return result

    def _transform_tuples(self, value: tuple[int, int]) -> tuple[int, int]:
        values = self._transform_array(value=np.array(value, dtype=int))
        return int(values[0]), int(values[1])

    def fromUHD(self) -> tuple[UiOffsetsModel, UiPosModel, UiRoiModel, dict[str, Template]]:
        offsets = UiOffsetsModel(
            find_bullet_points_width=self._transform(value=POSITIONS[1].find_bullet_points_width),
            find_seperator_short_offset_top=self._transform(value=POSITIONS[1].find_seperator_short_offset_top),
            item_descr_line_height=self._transform(value=POSITIONS[1].item_descr_line_height),
            item_descr_off_bottom_edge=self._transform(value=POSITIONS[1].item_descr_off_bottom_edge),
            item_descr_pad=self._transform(value=POSITIONS[1].item_descr_pad),
            item_descr_width=self._transform(value=POSITIONS[1].item_descr_width),
            vendor_center_item_x=self._transform(value=POSITIONS[1].vendor_center_item_x),
        )
        pos = UiPosModel(
            possible_centers=self._transform_list_of_tuples(value=POSITIONS[2].possible_centers),
            window_dimensions=self._transform_tuples(value=POSITIONS[2].window_dimensions),
        )
        roi = UiRoiModel(
            rel_descr_search_left=self._transform_array(value=POSITIONS[3].rel_descr_search_left, scale_only=True),
            rel_descr_search_right=self._transform_array(value=POSITIONS[3].rel_descr_search_right, scale_only=True),
            rel_fav_flag=self._transform_array(value=POSITIONS[3].rel_fav_flag, scale_only=True),
            slots_8x1=self._transform_array(value=POSITIONS[3].slots_8x1),
            slots_3x11=self._transform_array(value=POSITIONS[3].slots_3x11),
            slots_5x10=self._transform_array(value=POSITIONS[3].slots_5x10),
            sort_icon=self._transform_array(value=POSITIONS[3].sort_icon),
            stash_menu_icon=self._transform_array(value=POSITIONS[3].stash_menu_icon),
            tab_slots=self._transform_array(value=POSITIONS[3].tab_slots),
            vendor_menu_icon=self._transform_array(value=POSITIONS[3].vendor_menu_icon),
        )
        templates = self._transform_templates(load_templates())
        return offsets, pos, roi, templates


@singleton
class ResManager:
    def __init__(self):
        self._current_resolution = "3840x2160"
        self._offsets = POSITIONS[1]
        self._pos = POSITIONS[2]
        self._roi = POSITIONS[3]
        self._templates = load_templates()

    @property
    def offsets(self) -> UiOffsetsModel:
        return self._offsets

    @property
    def pos(self) -> UiPosModel:
        return self._pos

    @property
    def resolution(self) -> tuple[int, ...]:
        return tuple(map(int, self._current_resolution.split("x")))

    @property
    def roi(self) -> UiRoiModel:
        return self._roi

    @property
    def templates(self) -> dict[str, Template]:
        return self._templates

    def set_resolution(self, res: str):
        if res == self._current_resolution:
            return
        self._current_resolution = res
        LOGGER.info(f"Setting ui resolution to {res}")
        self._offsets, self._pos, self._roi, self._templates = _ResTransformer(resolution=res).fromUHD()
