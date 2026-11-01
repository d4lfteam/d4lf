from src.paragon.overlay.contracts import ParagonOverlayContract
from src.paragon.overlay.ui import OverlayUIMixin


def test_overlay_ui_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayUIMixin, ParagonOverlayContract)
