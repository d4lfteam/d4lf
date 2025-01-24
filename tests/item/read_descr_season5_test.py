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

BASE_PATH = BASE_DIR / "tests/assets/item/season5"

items = [
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_medium_read_descr_1.png",
        item1 := Item(
            affixes=[
                Affix(name="intelligence", value=101, type=AffixType.rerolled),
                Affix(name="maximum_life", value=1155),
                Affix(name="maximum_resource", value=10),
                Affix(name="lucky_hit_up_to_a_chance_to_stun_for_seconds", value=17.2, type=AffixType.tempered),
                Affix(name="to_warmth", value=1, type=AffixType.tempered),
            ],
            item_type=ItemType.Helm,
            power=914,
            rarity=ItemRarity.Legendary,
        ),
    ),
    ((3840, 2160), f"{BASE_PATH}/2160p_small_read_descr_1.png", item1),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_medium_read_descr_2.png",
        item2 := Item(
            affixes=[
                Affix(name="intelligence", value=87),
                Affix(name="maximum_life", value=1441, type=AffixType.greater),
                Affix(name="mana_per_second", value=6, type=AffixType.rerolled),
                Affix(name="lucky_hit_up_to_a_chance_to_stun_for_seconds", value=15.5, type=AffixType.tempered),
                Affix(name="to_warmth", value=2, type=AffixType.tempered),
            ],
            item_type=ItemType.ChestArmor,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    ((3840, 2160), f"{BASE_PATH}/2160p_small_read_descr_2.png", item2),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_medium_read_descr_3.png",
        item3 := Item(
            affixes=[
                Affix(name="intelligence", value=90),
                Affix(name="attack_speed", value=9.8, type=AffixType.rerolled),
                Affix(name="lucky_hit_up_to_a_chance_to_restore_primary_resource", value=12.1),
                Affix(name="lucky_hit_up_to_a_chance_to_stun_for_seconds", value=20.1, type=AffixType.tempered),
                Affix(name="shock_critical_strike_damage", value=97.8, type=AffixType.tempered),
            ],
            item_type=ItemType.Gloves,
            power=854,
            rarity=ItemRarity.Legendary,
        ),
    ),
    ((3840, 2160), f"{BASE_PATH}/2160p_small_read_descr_3.png", item3),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_medium_read_descr_8.png",
        item8 := Item(
            affixes=[
                Affix(name="intelligence", value=92),
                Affix(name="attack_speed", value=17.1, type=AffixType.greater),
                Affix(name="critical_strike_chance", value=6.9, type=AffixType.rerolled),
                Affix(name="vulnerable_damage", value=56.3, type=AffixType.tempered),
                Affix(name="unstable_currents_cooldown_reduction", value=14.4, type=AffixType.tempered),
            ],
            inherent=[
                Affix(name="resistance_to_all_elements", value=10, type=AffixType.inherent),
                Affix(name="shadow_resistance", value=10, type=AffixType.inherent),
            ],
            item_type=ItemType.Ring,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    ((3840, 2160), f"{BASE_PATH}/2160p_small_read_descr_8.png", item8),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_medium_read_descr_9.png",
        item9 := Item(
            affixes=[
                Affix(name="intelligence", value=6.3),
                Affix(name="maximum_life", value=1441, type=AffixType.greater),
                Affix(name="cooldown_reduction", value=10.5, type=AffixType.rerolled),
                Affix(name="unstable_currents_cooldown_reduction", value=13.2, type=AffixType.tempered),
                Affix(name="overpower_damage", value=86.2, type=AffixType.tempered),
            ],
            inherent=[Affix(name="resistance_to_all_elements", value=23.8, type=AffixType.inherent)],
            item_type=ItemType.Amulet,
            power=872,
            rarity=ItemRarity.Legendary,
        ),
    ),
    ((3840, 2160), f"{BASE_PATH}/2160p_small_read_descr_9.png", item9),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_medium_read_descr_11.png",
        item11 := Item(
            affixes=[
                Affix(name="movement_speed", value=19),
                Affix(name="maximum_resistance_to_all_elements", value=14.3, type=AffixType.greater),
                Affix(name="resistance_to_all_elements", value=69),
                Affix(name="damage_reduction", value=23),
            ],
            aspect=Aspect(name="tyraels_might", value=4996),
            inherent=[Affix(name="ignore_durability_loss", value=None, type=AffixType.inherent)],
            item_type=ItemType.ChestArmor,
            power=925,
            rarity=ItemRarity.Mythic,
        ),
    ),
    ((3840, 2160), f"{BASE_PATH}/2160p_small_read_descr_11.png", item11),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_small_read_descr_12.png",
        Item(
            affixes=[
                Affix(name="all_stats", value=98, type=AffixType.greater),
                Affix(name="attack_speed", value=8.5),
                Affix(name="cold_resistance", value=55.5),
                Affix(name="lucky_hit_up_to_a_chance_to_deal_cold_damage", value=40, type=AffixType.greater),
            ],
            aspect=Aspect(name="azurewrath", value=23825),
            inherent=[Affix(name="cold_damage", value=85, type=AffixType.inherent)],
            item_type=ItemType.Sword,
            power=925,
            rarity=ItemRarity.Unique,
        ),
    ),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_small_read_descr_13.png",
        Item(
            affixes=[
                Affix(name="attack_speed", value=11),
                Affix(name="fire_and_cold_damage", value=156),
                Affix(name="lucky_hit_up_to_a_chance_to_deal_fire_damage", value=40),
                Affix(name="lucky_hit_up_to_a_chance_to_deal_cold_damage", value=40, type=AffixType.greater),
            ],
            aspect=Aspect(name="frostburn", value=58),
            inherent=[Affix(name="lucky_hit_chance", value=8, type=AffixType.inherent)],
            item_type=ItemType.Gloves,
            power=925,
            rarity=ItemRarity.Unique,
        ),
    ),
    (
        (3840, 2160),
        f"{BASE_PATH}/2160p_small_read_descr_14.png",
        Item(
            affixes=[
                Affix(name="attack_speed", value=8),
                Affix(name="lightning_resistance", value=37),
                Affix(name="to_shocking_impact", value=1),
            ],
            inherent=[Affix(name="resistance_to_all_elements", value=25, type=AffixType.inherent)],
            item_type=ItemType.Amulet,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (2160, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_1.png",
        Item(
            affixes=[
                Affix(name="all_stats", value=3),
                Affix(name="maximum_resource", value=11),
                Affix(name="critical_strike_damage", value=94),
                Affix(name="resistance_to_all_elements", value=9),
            ],
            aspect=Aspect(name="locrans_talisman", value=0.19),
            inherent=[Affix(name="resistance_to_all_elements", value=25, type=AffixType.inherent)],
            item_type=ItemType.Amulet,
            power=925,
            rarity=ItemRarity.Unique,
        ),
    ),
    (
        (3440, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_2.png",
        Item(
            affixes=[
                Affix(name="intelligence", value=43),
                Affix(name="maximum_resource", value=7),
                Affix(name="lucky_hit_chance", value=4),
            ],
            item_type=ItemType.Helm,
            power=590,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (3440, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_3.png",
        Item(
            affixes=[
                Affix(name="intelligence", value=80),
                Affix(name="fire_resistance", value=34),
                Affix(name="to_basic_skills", value=2),
            ],
            item_type=ItemType.Legs,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (3440, 1440),
        f"{BASE_PATH}/1440p_small_read_descr_6.png",
        Item(
            affixes=[
                Affix(name="intelligence", value=77),
                Affix(name="maximum_life", value=794),
                Affix(name="damage_over_time", value=51),
            ],
            item_type=ItemType.Gloves,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_1.png",
        Item(
            affixes=[
                Affix(name="intelligence", value=87),
                Affix(name="essence_per_second", value=3, type=AffixType.rerolled),
                Affix(name="movement_speed", value=14.5),
                Affix(name="lucky_hit_up_to_a_chance_to_freeze_for_seconds", value=13, type=AffixType.tempered),
                Affix(name="movement_speed", value=9.5, type=AffixType.tempered),
            ],
            inherent=[Affix(name="attacks_reduce_evades_cooldown_by_seconds", value=1.5, type=AffixType.inherent)],
            item_type=ItemType.Boots,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_2.png",
        Item(
            affixes=[
                Affix(name="movement_speed", value=23.1),
                Affix(name="maximum_resistance_to_all_elements", value=8.6),
                Affix(name="resistance_to_all_elements", value=69),
                Affix(name="damage_reduction", value=23),
            ],
            aspect=Aspect(name="tyraels_might", value=5213),
            inherent=[Affix(name="ignore_durability_loss", value=None, type=AffixType.inherent)],
            item_type=ItemType.ChestArmor,
            power=925,
            rarity=ItemRarity.Mythic,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_3.png",
        Item(
            affixes=[
                Affix(name="maximum_life", value=950),
                Affix(name="cooldown_reduction", value=9.1, type=AffixType.rerolled),
                Affix(name="to_conjuration_skills", value=2),
                Affix(name="unstable_currents_cooldown_reduction", value=16.1, type=AffixType.tempered),
                Affix(name="overpower_damage", value=80.5, type=AffixType.tempered),
            ],
            inherent=[Affix(name="resistance_to_all_elements", value=25, type=AffixType.inherent)],
            item_type=ItemType.Amulet,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_4.png",
        Item(
            affixes=[
                Affix(name="maximum_life", value=1342),
                Affix(name="life_on_hit", value=39),
                Affix(name="lucky_hit_up_to_a_chance_to_restore_primary_resource", value=23),
            ],
            inherent=[Affix(name="damage_over_time", value=40, type=AffixType.inherent)],
            item_type=ItemType.Staff,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_5.png",
        Item(
            affixes=[
                Affix(name="intelligence", value=149, type=AffixType.greater),
                Affix(name="maximum_life", value=1441, type=AffixType.greater),
                Affix(name="to_flame_shield", value=3, type=AffixType.rerolled),
                Affix(name="flame_shield_duration", value=17.2, type=AffixType.tempered),
                Affix(name="frost_nova_size", value=47.6, type=AffixType.tempered),
            ],
            item_type=ItemType.ChestArmor,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1915, 1005),
        f"{BASE_PATH}/1080p_small_read_descr_6.png",
        Item(
            affixes=[
                Affix(name="intelligence", value=198, type=AffixType.rerolled),
                Affix(name="maximum_life", value=2882, type=AffixType.greater),
                Affix(name="critical_strike_damage", value=108.1),
                Affix(name="critical_strike_damage", value=210, type=AffixType.tempered),
                # image quality is so bad it reads 70.19 instead of 70.1
                Affix(name="chance_for_a_second_lightning_spear_when_cast", value=70.19, type=AffixType.tempered),
            ],
            inherent=[Affix(name="damage_over_time", value=40, type=AffixType.inherent)],
            item_type=ItemType.Staff,
            power=925,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_small_read_descr_7.png",
        Item(
            affixes=[
                Affix(name="maximum_life", value=665),
                Affix(name="maximum_resource", value=13),
                Affix(name="critical_strike_chance", value=7.0),
            ],
            inherent=[Affix(name="lucky_hit_chance", value=10, type=AffixType.inherent)],
            item_type=ItemType.Focus,
            power=876,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_medium_read_descr_1.png",
        Item(
            affixes=[
                Affix(name="strength", value=77),
                Affix(name="armor", value=1290, type=AffixType.rerolled),
                Affix(name="critical_strike_chance", value=8),
            ],
            item_type=ItemType.Gloves,
            power=794,
            rarity=ItemRarity.Legendary,
        ),
    ),
    (
        (1920, 1080),
        f"{BASE_PATH}/1080p_medium_read_descr_2.png",
        Item(
            affixes=[
                Affix(name="movement_speed", value=21.4),
                Affix(name="maximum_resistance_to_all_elements", value=9.8),
                Affix(name="resistance_to_all_elements", value=78),
                Affix(name="damage_reduction", value=36),
            ],
            aspect=Aspect(name="tyraels_might", value=5213),
            inherent=[Affix(name="ignore_durability_loss", value=None, type=AffixType.inherent)],
            item_type=ItemType.ChestArmor,
            power=925,
            rarity=ItemRarity.Mythic,
        ),
    ),
]


def _run_test_helper(img_res: tuple[int, int], input_img: str, expected_item: Item):
    Cam().update_window_pos(0, 0, *img_res)
    img = cv2.imread(input_img)
    item = read_descr(expected_item.rarity, img)
    assert item == expected_item


@pytest.mark.parametrize(("img_res", "input_img", "expected_item"), items)
def test_item(img_res: tuple[int, int], input_img: str, expected_item: Item):
    _run_test_helper(img_res=img_res, input_img=input_img, expected_item=expected_item)
