import numpy as np
import pytest
from pydantic import ValidationError

from src.settings.models_ui import HSVRangeModel, UiRoiModel


def _roi() -> UiRoiModel:
    values = np.array([1, 2, 3, 4])
    return UiRoiModel(
        rel_descr_search_left=values,
        rel_descr_search_right=values,
        rel_fav_flag=values,
        slots_8x1=values,
        slots_3x11=values,
        slots_5x10=values,
        sort_icon=values,
        stash_menu_icon=values,
        tab_slots=values,
        vendor_menu_icon=values,
    )


def test_hsv_range_supports_indexing() -> None:
    model = HSVRangeModel(h_s_v_min=np.array([1, 2, 3]), h_s_v_max=np.array([4, 5, 6]))
    assert np.array_equal(model[0], np.array([1, 2, 3]))


def test_hsv_range_rejects_invalid_interval() -> None:
    with pytest.raises(ValidationError):
        HSVRangeModel(h_s_v_min=np.array([4, 2, 3]), h_s_v_max=np.array([1, 5, 6]))


def test_ui_models_keep_numpy_arrays() -> None:
    roi = _roi()
    assert np.array_equal(roi.rel_fav_flag, np.array([1, 2, 3, 4]))
