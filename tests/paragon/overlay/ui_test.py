from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.ui import OverlayUIMixin


def test_overlay_ui_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayUIMixin, OverlayContract)
