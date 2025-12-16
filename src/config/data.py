"""Everything is this file is based on UHD resolution (3840x2160)."""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from src.config import BASE_DIR
from src.config.loader import IniConfigLoader
from src.config.models import (
    ColorsModel,
    HSVRangeModel,
    UiOffsetsModel,
    UiPosModel,
    UiRoiModel,
)
from src.utils.image_operations import alpha_to_mask

LOGGER = logging.getLogger("d4lf")

COLORS = ColorsModel(
    material_color=HSVRangeModel(h_s_v_min=np.array([86, 110, 190]), h_s_v_max=np.array([114, 220, 255])),
    unique_gold=HSVRangeModel(h_s_v_min=np.array([4, 45, 125]), h_s_v_max=np.array([26, 155, 250])),
    unusable_red=HSVRangeModel(h_s_v_min=np.array([0, 210, 110]), h_s_v_max=np.array([10, 255, 210])),
)

TAB_SLOTS_COORDS = {6: np.array([300, 284, 800, 102]), 7: np.array([240, 292, 930, 106])}

POSITIONS = (
    (3840, 2160),
    UiOffsetsModel(
        find_bullet_points_width=150,
        find_seperator_short_offset_top=500,
        item_descr_line_height=50,
        item_descr_off_bottom_edge=104,
        item_descr_pad=30,
        item_descr_width=780,
        vendor_center_item_x=1232,
    ),
    UiPosModel(
        possible_centers=[
            (2994, 244),
            (2994, 432),
            (2994, 624),
            (2994, 810),
            (2994, 992),
            (2994, 1196),
            (3722, 428),
            (3722, 618),
            (3722, 808),
            (3614, 1220),
            (3730, 1220),
            (3304, 1218),
            (3416, 1218),
        ],
        window_dimensions=(3840, 2160),
    ),
    UiRoiModel(
        rel_descr_search_left=np.array([-900, 0, 150, 1760]),
        rel_descr_search_right=np.array([60, 0, 120, 1760]),
        rel_fav_flag=np.array([8, 6, 16, 20]),
        slots_8x1=np.array([1166, 165, 125, 1462]),
        slots_3x11=np.array([2536, 1444, 1214, 486]),
        slots_5x10=np.array([92, 538, 1224, 972]),
        sort_icon=np.array([2440, 1332, 126, 124]),
        stash_menu_icon=np.array([592, 144, 218, 96]),
        tab_slots=TAB_SLOTS_COORDS[IniConfigLoader().general.max_stash_tabs],
        vendor_menu_icon=np.array([182, 757, 220, 90]),
    ),
)


@dataclass
class Template:
    name: str = None
    img_bgra: np.ndarray = None
    img_bgr: np.ndarray = None
    img_gray: np.ndarray = None
    alpha_mask: np.ndarray = None


@lru_cache
def load_templates() -> dict[str, Template]:
    result = {}
    template_paths = Path(BASE_DIR / "assets/templates").rglob("*.png")
    for template in template_paths:
        try:
            template_img = cv2.imread(str(template), cv2.IMREAD_UNCHANGED)
        except cv2.error:
            LOGGER.exception(f"Could not load image: {template}")
            continue
        result[template.stem.lower()] = Template(
            name=template.stem.lower(),
            img_bgra=template_img,
            img_bgr=cv2.cvtColor(template_img, cv2.COLOR_BGRA2BGR),
            img_gray=cv2.cvtColor(template_img, cv2.COLOR_BGRA2GRAY),
            alpha_mask=alpha_to_mask(template_img),
        )
    return result
