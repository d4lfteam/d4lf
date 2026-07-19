import cv2
import pytest

from src.automation import stash_inventory
from src.automation.stash import Stash
from src.perception import update_window_position
from src.settings import BASE_DIR

BASE_PATH = BASE_DIR / "tests/assets/ui"


def test_stash_is_configured_as_stash_menu(monkeypatch):
    monkeypatch.setattr(
        "src.automation.stash.get_ui_coordinates",
        lambda: type(
            "C",
            (),
            {
                "roi": type(
                    "R", (), {"slots_4x10": (0, 0, 100, 100), "rel_fav_flag": (0, 0, 1, 1), "stash_tab": (0, 0, 1, 1)}
                )()
            },
        )(),
    )
    stash = Stash()
    assert stash.menu_name == "Stash"


@pytest.mark.parametrize("img_res", [(3440, 1440)])
def test_stash_detects_open_chest(img_res):
    update_window_position(0, 0, *img_res)
    image = cv2.imread(f"{BASE_PATH}/chest_open_1440p_wide.png")

    assert stash_inventory().is_open(image)
