import cv2
import pytest

from src.cam import Cam
from src.settings import BASE_DIR
from src.ui.char_inventory import CharInventory

BASE_PATH = BASE_DIR / "tests/assets/ui"


@pytest.mark.parametrize(
    ("img_res", "input_img"),
    [
        ((1920, 1080), f"{BASE_PATH}/char_inv_open_1080p.png"),
        ((2560, 1440), f"{BASE_PATH}/char_inv_open_1440p.png"),
        ((3440, 1440), f"{BASE_PATH}/char_inv_open_1440p_wide.png"),
        ((5120, 1440), f"{BASE_PATH}/char_inv_open_1440p_ultra_wide.png"),
        ((3840, 2160), f"{BASE_PATH}/char_inv_open_2160p.png"),
    ],
)
def test_char_inventory(img_res, input_img):
    Cam().update_window_pos(0, 0, *img_res)
    img = cv2.imread(input_img)
    inv = CharInventory()
    flag = inv.is_open(img)
    assert flag


@pytest.mark.parametrize(
    ("img_res", "input_img", "occupied", "junk", "fav"),
    [
        ((1920, 1080), f"{BASE_PATH}/char_inventory_fav_junk_1080p.png", 13, 2, 7),
        ((1920, 1080), f"{BASE_PATH}/char_inventory_fav_junk_1080p_2.png", 31, 18, 3),
        ((3440, 1440), f"{BASE_PATH}/char_inv_open_1440p_wide.png", 12, 0, 0),
    ],
)
def test_get_item_slots(img_res, input_img, occupied, junk, fav):
    Cam().update_window_pos(0, 0, *img_res)
    img = cv2.imread(input_img)
    if img is None:
        pytest.fail(f"Unable to load test image: {input_img}")
    inv = CharInventory()
    occupied_slots, is_open = inv.get_item_slots(img)
    num_junk = 0
    num_fav = 0
    for slot in occupied_slots:
        if slot.is_fav:
            num_fav += 1
            cv2.circle(img, slot.center, 5, (0, 255, 0), 4)
        elif slot.is_junk:
            num_junk += 1
            cv2.circle(img, slot.center, 5, (0, 0, 255), 4)
        else:
            cv2.circle(img, slot.center, 5, (255, 0, 0), 4)
    for slot in is_open:
        cv2.circle(img, slot.center, 5, (255, 255, 0), 4)
    if False:
        cv2.imshow("char_inv", img)
        cv2.waitKey(0)
    assert occupied == len(occupied_slots)
    assert fav == num_fav
    assert junk == num_junk
