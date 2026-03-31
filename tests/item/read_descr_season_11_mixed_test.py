import cv2
import numpy as np
import pytest

import src.item.descr.read_descr_tts
import src.tts
from src.cam import Cam
from src.config import BASE_DIR
from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.data.seasonal_attribute import SeasonalAttribute
from src.item.descr.read_descr_tts import read_descr_mixed
from src.item.models import Item
from src.template_finder import TemplateMatch

BASE_PATH = BASE_DIR / "tests/assets/item/season11"

items = [
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_shield1.png",
        [
            "WILDBOLT AEGIS",
            "Legendary Shield",
            "750 Item Power",
            "844 Armor (-2.1% Toughness)",
            "41% Blocked Damage Reduction [41]%",
            "20% Block Chance [20]%",
            "+100% Main Hand Weapon Damage [100]%",
            "+99 Strength +[89 - 99]",
            "+272 Maximum Life [244 - 272]",
            "10.8% Damage Reduction [7.8 - 12.0]%",
            "8.4% Cooldown Reduction [8.1 - 8.8]%",
            "Every 3.5 [3.5 - 2.0] seconds, Distant enemies are Pulled In to you and take 10%[x] increased damage for 3 seconds. This effect cannot occur while you are in Stealth.",
            "Empty Socket",
            "Requires Level 60",
            "Sell Value: 27,947 Gold",
            "Durability: 100/100. Tempers: 3/3",
            "Right mouse button",
        ],
        8,
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_shield2.png",
        [
            "STORMSHIELD OF THE JUGGERNAUTS COVENANT",
            "Legendary Shield",
            "750 Item Power",
            "844 Armor (-3.2% Toughness)",
            "41% Blocked Damage Reduction [41]%",
            "20% Block Chance [20]%",
            "+100% Main Hand Weapon Damage [100]%",
            "+97 Strength +[89 - 99]",
            "+250 Maximum Life [244 - 272]",
            "+88 Life On Hit [84 - 92]",
            "10.2% Damage Reduction [7.8 - 12.0]%",
            "Consuming Resolve stacks with Juggernaut Oath grants an additional 68%[x] [60 - 90]% damage.",
            "Requires Level 60. Lord of Hatred Item",
            "Sell Value: 25,797 Gold",
            "Durability: 100/100. Tempers: 3/3",
            "Right mouse button",
        ],
        8,
    ),
    (
        (2560, 1440),
        f"{BASE_PATH}/1440p_small_shield3.png",
        [
            "PROTECTING DREAD SHIELD",
            "Ancestral Legendary Shield",
            "800 Item Power",
            "1,131 Armor (-5.1% Toughness)",
            "45% Blocked Damage Reduction [45]%",
            "20% Block Chance [20]%",
            "+100% Main Hand Weapon Damage [100]%",
            "+116 Strength +[107 - 121]",
            "+30.0% Healing Received",
            "13.0% Damage Reduction [11.5 - 15.7]%",
            "8.5% Cooldown Reduction [8.1 - 8.8]%",
            "When hit while not Healthy, you form a protective bubble that grants all Players inside Immune. The bubble lasts for 6.0 [2.5 - 6.0] seconds and can only form once every 90 seconds.",
            "Requires Level 60",
            "Upgrades an Aspect in the Codex of Power on salvage",
            "Sell Value: 26,475 Gold",
            "Durability: 100/100. Tempers: 4/4",
            "Right mouse button",
        ],
        8,
    ),
]


def _run_test_helper(img_res: tuple[int, int], input_img: str, tts: list[str], expected_affix_bullet_count: int):
    Cam().update_window_pos(0, 0, *img_res)
    src.tts.LAST_ITEM = tts
    img = cv2.imread(input_img)
    item = read_descr_mixed(img)
    total_affix_count = 0
    for affix in [*item.affixes, *item.inherent]:
        total_affix_count += 1 if affix.loc else 0
    total_affix_count += 1 if item.aspect.loc else 0
    assert total_affix_count == expected_affix_bullet_count


@pytest.mark.parametrize(("img_res", "input_img", "tts", "expected_affix_bullet_count"), items)
def test_item(img_res: tuple[int, int], input_img: str, tts: list[str], expected_affix_bullet_count: int):
    _run_test_helper(
        img_res=img_res, input_img=input_img, tts=tts, expected_affix_bullet_count=expected_affix_bullet_count
    )


def test_add_affixes_from_tts_mixed_raises_when_one_bullet_is_missing(monkeypatch):
    def fake_get_affix_starting_location_from_tts_section(_tts_section, _item):
        return 0

    def fake_get_affix_counts(_tts_section, _item, _start):
        return (1, 1)

    def fake_get_affixes_from_tts_section(_tts_section, _start, _length):
        return ["Armor", ""]

    def fake_get_aspect_from_tts_section(*_args, **_kwargs):
        return None

    def fake_screenshot(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        src.item.descr.read_descr_tts,
        "_get_affix_starting_location_from_tts_section",
        fake_get_affix_starting_location_from_tts_section,
    )
    monkeypatch.setattr(src.item.descr.read_descr_tts, "_get_affix_counts", fake_get_affix_counts)
    monkeypatch.setattr(
        src.item.descr.read_descr_tts, "_get_affixes_from_tts_section", fake_get_affixes_from_tts_section
    )
    monkeypatch.setattr(src.item.descr.read_descr_tts, "_get_aspect_from_tts_section", fake_get_aspect_from_tts_section)
    monkeypatch.setattr(src.item.descr.read_descr_tts, "screenshot", fake_screenshot)

    item = Item(item_type=ItemType.Helm, rarity=ItemRarity.Legendary, name="test_legendary")
    affix_bullets = [TemplateMatch(center=(10, 20), name="affix_bullet_point_1")]

    with pytest.raises(IndexError, match="Found more affixes than we found bullets"):
        src.item.descr.read_descr_tts._add_affixes_from_tts_mixed(
            tts_section=[],
            item=item,
            affix_bullets=affix_bullets,
            img_item_descr=np.zeros((1, 1, 3), dtype=np.uint8),
            aspect_bullet=None,
        )


def test_add_affixes_from_tts_mixed_allows_missing_last_bloodied_bullet(monkeypatch):
    def fake_get_affix_starting_location_from_tts_section(_tts_section, _item):
        return 0

    def fake_get_affix_counts(_tts_section, _item, _start):
        return (0, 4)

    def fake_get_affixes_from_tts_section(_tts_section, _start, _length):
        return ["first", "second", "third", "Hunger"]

    def fake_get_aspect_from_tts_section(*_args, **_kwargs):
        return None

    def fake_get_affix_from_text(text):
        return Affix(name=text, text=text)

    def fail_if_called(*_args, **_kwargs):
        msg = "_raise_index_error should not be called for the missing bloodied bullet fallback"
        raise AssertionError(msg)

    monkeypatch.setattr(
        src.item.descr.read_descr_tts,
        "_get_affix_starting_location_from_tts_section",
        fake_get_affix_starting_location_from_tts_section,
    )
    monkeypatch.setattr(src.item.descr.read_descr_tts, "_get_affix_counts", fake_get_affix_counts)
    monkeypatch.setattr(
        src.item.descr.read_descr_tts, "_get_affixes_from_tts_section", fake_get_affixes_from_tts_section
    )
    monkeypatch.setattr(src.item.descr.read_descr_tts, "_get_aspect_from_tts_section", fake_get_aspect_from_tts_section)
    monkeypatch.setattr(src.item.descr.read_descr_tts, "_get_affix_from_text", fake_get_affix_from_text)
    monkeypatch.setattr(src.item.descr.read_descr_tts, "_raise_index_error", fail_if_called)

    item = Item(
        item_type=ItemType.Ring,
        rarity=ItemRarity.Legendary,
        name="bloodied_ring",
        seasonal_attribute=SeasonalAttribute.bloodied,
    )
    affix_bullets = [
        TemplateMatch(center=(10, 20), name="affix_bullet_point_1"),
        TemplateMatch(center=(10, 40), name="affix_bullet_point_1"),
        TemplateMatch(center=(10, 60), name="affix_bullet_point_1"),
    ]

    result = src.item.descr.read_descr_tts._add_affixes_from_tts_mixed(
        tts_section=[],
        item=item,
        affix_bullets=affix_bullets,
        img_item_descr=np.zeros((1, 1, 3), dtype=np.uint8),
        aspect_bullet=None,
    )

    assert [affix.name for affix in result.affixes] == ["first", "second", "third", "Hunger"]
    assert result.affixes[0].loc == (10, 20)
    assert result.affixes[1].loc == (10, 40)
    assert result.affixes[2].loc == (10, 60)
    assert result.affixes[3].loc is None
