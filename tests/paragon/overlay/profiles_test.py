from src.paragon.overlay.profiles import OverlayUIMixin
from src.paragon.shared import OverlayContract


def test_overlay_profiles_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayUIMixin, OverlayContract)
