from types import SimpleNamespace

from src.item.data.aspect import Aspect
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr import parse_aspect


class DummyDataloader:
    def __init__(self, aspect_list=None):
        self.aspect_list = aspect_list or []


def test_parse_aspect_from_tts_section_mythic_uses_item_name_and_number(monkeypatch):
    monkeypatch.setattr(parse_aspect, "Dataloader", lambda: DummyDataloader())

    item = SimpleNamespace(rarity=ItemRarity.Mythic, name="black_river")
    aspect = parse_aspect.parse_aspect_from_tts_section(
        ["BLACK RIVER", "Mythic Sword", "Damage", "Your core skills deal 12% increased damage"],
        item,
        start=0,
        num_affixes=3,
    )

    assert aspect == Aspect(name="black_river", text="Your core skills deal 12% increased damage", value=12.0)


def test_parse_aspect_from_tts_section_unique_parses_ranges(monkeypatch):
    monkeypatch.setattr(parse_aspect, "Dataloader", lambda: DummyDataloader())

    item = SimpleNamespace(rarity=ItemRarity.Unique, name="tibaults_will")
    aspect = parse_aspect.parse_aspect_from_tts_section(
        ["TIBAULT'S WILL", "Unique Pants", "Damage", "You deal 30 [20 - 40] increased damage"],
        item,
        start=0,
        num_affixes=3,
    )

    assert aspect.name == "tibaults_will"
    assert aspect.text == "You deal 30 [20 - 40] increased damage"
    assert aspect.value == 30.0
    assert aspect.min_value == 20.0
    assert aspect.max_value == 40.0


def test_parse_aspect_from_tts_section_legendary_uses_known_aspect_name(monkeypatch):
    monkeypatch.setattr(parse_aspect, "Dataloader", lambda: DummyDataloader(["of_occult_dominion", "accelerating"]))

    item = SimpleNamespace(rarity=ItemRarity.Legendary, name="legendary_ring_of_occult_dominion")
    aspect = parse_aspect.parse_aspect_from_tts_section(
        ["LEGENDARY RING", "Legendary Ring", "Damage", "You deal 25% increased damage"],
        item,
        start=0,
        num_affixes=3,
    )

    assert aspect == Aspect(name="of_occult_dominion", text="You deal 25% increased damage")


def test_get_aspect_text_returns_none_for_non_aspect_items():
    assert parse_aspect.get_aspect_text(["a", "b"], ItemRarity.Rare, 0, 2) is None
