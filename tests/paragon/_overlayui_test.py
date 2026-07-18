from src.paragon._overlayui import OverlayUIMixin
from src.paragon._shared import OverlayContract


def test_overlay_ui_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayUIMixin, OverlayContract)
