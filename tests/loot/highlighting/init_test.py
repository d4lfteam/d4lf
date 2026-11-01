from src.loot import highlighting


def test_highlighting_public_interface() -> None:
    assert highlighting.__all__ == ["HighlightingVisionMode", "create_highlighting_vision_mode"]
    assert all(hasattr(highlighting, name) for name in highlighting.__all__)
