import cv2
import pytest

from src.cam import Cam
from src.config import BASE_DIR
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr import read_descr
from src.item.models import Item

BASE_PATH = BASE_DIR / "tests/assets/item/season6"

items = []

materials = [
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_compass_1.png",
        Item(
            item_type=ItemType.Material,
            rarity=ItemRarity.Common,
        ),
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_rune_magic_1.png",
        Item(
            item_type=ItemType.Material,
            rarity=ItemRarity.Magic,
        ),
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_rune_magic_2.png",
        Item(
            item_type=ItemType.Material,
            rarity=ItemRarity.Magic,
        ),
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_rune_rare_1.png",
        Item(
            item_type=ItemType.Material,
            rarity=ItemRarity.Rare,
        ),
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_rune_rare_2.png",
        Item(
            item_type=ItemType.Material,
            rarity=ItemRarity.Rare,
        ),
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_tribute_magic_1.png",
        Item(
            item_type=ItemType.Material,
            rarity=ItemRarity.Magic,
        ),
    ),
]

sigils = [
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_sigil_1.png",
        Item(
            affixes=[Affix(name="ancestors_favor"), Affix(name="monster_barrier")],
            inherent=[Affix(name="carrion_fields", type=AffixType.inherent)],
            item_type=ItemType.Sigil,
            rarity=ItemRarity.Common,
        ),
    )
]


def _run_test_helper(img_res: tuple[int, int], input_img: str, expected_item: Item):
    Cam().update_window_pos(0, 0, *img_res)
    img = cv2.imread(input_img)
    item = read_descr(expected_item.rarity, img)
    assert item == expected_item


@pytest.mark.parametrize(("img_res", "input_img", "expected_item"), items)
def test_items(img_res: tuple[int, int], input_img: str, expected_item: Item):
    _run_test_helper(img_res=img_res, input_img=input_img, expected_item=expected_item)


@pytest.mark.parametrize(("img_res", "input_img", "expected_item"), materials)
def test_materials(img_res: tuple[int, int], input_img: str, expected_item: Item):
    _run_test_helper(img_res=img_res, input_img=input_img, expected_item=expected_item)


@pytest.mark.parametrize(("img_res", "input_img", "expected_item"), sigils)
def test_sigils(img_res: tuple[int, int], input_img: str, expected_item: Item):
    _run_test_helper(img_res=img_res, input_img=input_img, expected_item=expected_item)
