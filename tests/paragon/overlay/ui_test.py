from src.paragon.overlay.ui import OverlayUIMixin
from src.paragon.shared import OverlayContract


def test_overlay_ui_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayUIMixin, OverlayContract)
