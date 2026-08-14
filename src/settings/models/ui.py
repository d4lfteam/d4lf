from typing import Annotated

import numpy as np
from pydantic import field_validator, model_validator
from pydantic_numpy.helper.annotation import NpArrayPydanticAnnotation
from pydantic_numpy.model import NumpyModel

from src.settings.models.core import _IniBaseModel

type Np1DArray = Annotated[
    np.ndarray[tuple[int, ...], np.dtype[np.generic]],
    NpArrayPydanticAnnotation.factory(data_type=None, dimensions=1, strict_data_typing=False),
]


class HSVRangeModel(_IniBaseModel):
    h_s_v_min: Np1DArray
    h_s_v_max: Np1DArray

    def __getitem__(self, index: int) -> Np1DArray:
        # TODO added this to not have to change much of the other code. should be fixed some time
        if index == 0:
            return self.h_s_v_min
        if index == 1:
            return self.h_s_v_max
        msg = "Index out of range"
        raise IndexError(msg)

    @model_validator(mode="after")
    def check_interval_sanity(self) -> HSVRangeModel:
        if self.h_s_v_min[0] > self.h_s_v_max[0]:
            msg = f"invalid hue range [{self.h_s_v_min[0]}, {self.h_s_v_max[0]}]"
            raise ValueError(msg)
        if self.h_s_v_min[1] > self.h_s_v_max[1]:
            msg = f"invalid saturation range [{self.h_s_v_min[1]}, {self.h_s_v_max[1]}]"
            raise ValueError(msg)
        if self.h_s_v_min[2] > self.h_s_v_max[2]:
            msg = f"invalid value range [{self.h_s_v_min[2]}, {self.h_s_v_max[2]}]"
            raise ValueError(msg)
        return self

    @field_validator("h_s_v_min", "h_s_v_max")
    @classmethod
    def values_in_range(cls, v: np.ndarray) -> np.ndarray:
        if len(v) != 3:
            msg = "must be h,s,v"
            raise ValueError(msg)
        if not -179 <= v[0] <= 179:
            msg = "must be in [-179, 179]"
            raise ValueError(msg)
        if not all(0 <= x <= 255 for x in v[1:3]):
            msg = "must be in [0, 255]"
            raise ValueError(msg)
        return v


class ColorsModel(_IniBaseModel):
    material_color: HSVRangeModel
    unique_gold: HSVRangeModel
    unusable_red: HSVRangeModel


class UiOffsetsModel(_IniBaseModel):
    find_bullet_points_width: int
    find_seperator_short_offset_top: int
    item_descr_line_height: int
    item_descr_off_bottom_edge: int
    item_descr_pad: int
    item_descr_width: int
    vendor_center_item_x: int


class UiPosModel(_IniBaseModel):
    possible_centers: list[tuple[int, int]]
    window_dimensions: tuple[int, int]


class UiRoiModel(NumpyModel):
    rel_descr_search_left: Np1DArray
    rel_descr_search_right: Np1DArray
    rel_fav_flag: Np1DArray
    slots_8x1: Np1DArray
    slots_3x11: Np1DArray
    slots_5x10: Np1DArray
    sort_icon: Np1DArray
    stash_menu_icon: Np1DArray
    tab_slots: Np1DArray
    vendor_menu_icon: Np1DArray
