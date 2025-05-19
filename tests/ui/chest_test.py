import cv2
import pytest

from src.cam import Cam
from src.config import BASE_DIR
from src.ui.stash import Stash

BASE_PATH = BASE_DIR / "tests/assets/ui"


@pytest.mark.parametrize(("img_res", "input_img"), [((3440, 1440), f"{BASE_PATH}/chest_open_1440p_wide.png")])
def test_chest(img_res, input_img):
    Cam().update_window_pos(0, 0, *img_res)
    img = cv2.imread(input_img)
    inv = Stash()
    flag = inv.is_open(img)
    assert flag
