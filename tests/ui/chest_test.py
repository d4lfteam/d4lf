import cv2
import pytest

from src.automation import stash_inventory
from src.perception._capture import Cam
from src.settings import BASE_DIR

BASE_PATH = BASE_DIR / "tests/assets/ui"


@pytest.mark.parametrize(("img_res", "input_img"), [((3440, 1440), f"{BASE_PATH}/chest_open_1440p_wide.png")])
def test_chest(img_res, input_img):
    Cam().update_window_pos(0, 0, *img_res)
    img = cv2.imread(input_img)
    inv = stash_inventory()
    flag = inv.is_open(img)
    assert flag
