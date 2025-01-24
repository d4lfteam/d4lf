import cv2
import pytest

from src.cam import Cam
from src.config import BASE_DIR
from src.item.data.affix import Affix, AffixType
from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr import read_descr
from src.item.models import Item

BASE_PATH = BASE_DIR / "tests/assets/item/season6"

items = [
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_1.png",
        Item(
            affixes=[
                Affix(name="maximum_life", value=266),
                Affix(name="cold_resistance", value=37),
                Affix(name="to_armored_hide", value=3),
            ],
            item_type=ItemType.ChestArmor,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_2.png",
        Item(
            affixes=[
                Affix(name="dexterity", value=8.4),
                Affix(name="movement_speed", value=20),
                Affix(name="to_brilliance", value=2),
            ],
            inherent=[Affix(name="resistance_to_all_elements", value=25, type=AffixType.inherent)],
            item_type=ItemType.Amulet,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (2160, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_1.png",
        Item(
            affixes=[
                Affix(name="dexterity", value=194),
                Affix(name="basic_lucky_hit_chance", value=5),
                Affix(name="chance_for_basic_skills_to_deal_double_damage", value=27),
                Affix(name="to_follow_through", value=2),
            ],
            aspect=Aspect(name="sepazontec", value=68),
            inherent=[Affix(name="block_chance", value=40, type=AffixType.inherent)],
            item_type=ItemType.Quarterstaff,
            power=750,
            rarity=ItemRarity.Unique,
        ),
    ),
    (
        (2160, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_2.png",
        Item(
            affixes=[
                Affix(name="maximum_resource", value=12),
                Affix(name="critical_strike_damage", value=90),
                Affix(name="chance_for_core_skills_to_hit_twice", value=52.5, type=AffixType.greater),
                Affix(name="to_velocity", value=3),
            ],
            aspect=Aspect(name="rod_of_kepeleke", value=0.5),
            inherent=[Affix(name="block_chance", value=45, type=AffixType.inherent)],
            item_type=ItemType.Quarterstaff,
            power=800,
            rarity=ItemRarity.Unique,
        ),
    ),
    (
        (2160, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_3.png",
        Item(
            affixes=[
                Affix(name="dexterity", value=97),
                Affix(name="maximum_life", value=255),
                Affix(name="poison_resistance", value=38),
            ],
            item_type=ItemType.ChestArmor,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (2160, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_4.png",
        Item(
            affixes=[
                Affix(name="dexterity", value=91),
                Affix(name="maximum_life", value=261),
                Affix(name="cold_resistance", value=40),
            ],
            item_type=ItemType.ChestArmor,
            power=750,
            rarity=ItemRarity.Legendary,
        ),
    ),
]

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
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_sigil_2.png",
        Item(
            affixes=[Affix(name="ancestors_favor"), Affix(name="monster_barrier")],
            inherent=[Affix(name="whispering_pines", type=AffixType.inherent)],
            item_type=ItemType.Sigil,
            rarity=ItemRarity.Common,
        ),
    ),
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
