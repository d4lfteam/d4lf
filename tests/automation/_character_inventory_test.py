import cv2
import pytest

from src.automation import character_inventory
from src.automation._character_inventory import CharInventory
from src.perception import update_window_position
from src.settings import BASE_DIR

BASE_PATH = BASE_DIR / "tests/assets/ui"


def test_character_inventory_uses_character_menu_name(monkeypatch):
    monkeypatch.setattr(
        "src.automation._character_inventory.get_ui_coordinates",
        lambda: type("C", (), {"roi": type("R", (), {"sort_icon": (1, 2, 3, 4)})()})(),
    )
    monkeypatch.setattr("src.automation._character_inventory.create_template_query", lambda **kwargs: kwargs)
    monkeypatch.setattr(
        "src.automation._character_inventory.get_settings",
        lambda: type("S", (), {"char": type("C", (), {"inventory": "i"})()})(),
    )
    inventory = CharInventory()
    assert inventory.menu_name == "Char_Inventory"
    assert inventory.open_hotkey == "i"


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
def test_character_inventory_detects_open_inventory(img_res, input_img):
    update_window_position(0, 0, *img_res)
    image = cv2.imread(input_img)

    assert character_inventory().is_open(image)


@pytest.mark.parametrize(
    ("img_res", "input_img", "occupied", "junk", "fav"),
    [
        ((1920, 1080), f"{BASE_PATH}/char_inventory_fav_junk_1080p.png", 13, 2, 7),
        ((1920, 1080), f"{BASE_PATH}/char_inventory_fav_junk_1080p_2.png", 31, 18, 3),
        ((3440, 1440), f"{BASE_PATH}/char_inv_open_1440p_wide.png", 12, 0, 0),
    ],
)
def test_character_inventory_classifies_item_slots(img_res, input_img, occupied, junk, fav):
    update_window_position(0, 0, *img_res)
    image = cv2.imread(input_img)
    if image is None:
        pytest.fail(f"Unable to load test image: {input_img}")

    occupied_slots, _ = character_inventory().get_item_slots(image)

    assert len(occupied_slots) == occupied
    assert sum(slot.is_junk for slot in occupied_slots) == junk
    assert sum(slot.is_fav for slot in occupied_slots) == fav
