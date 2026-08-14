from src import loot
from src.item import Item
from src.settings import VisionModeType


def test_factory_selects_fast_mode_through_public_facade(monkeypatch) -> None:
    expected = Item()
    monkeypatch.setattr("src.loot.fast.VisionModeFast", lambda: expected)
    assert loot.create_vision_mode(VisionModeType.fast) is expected
