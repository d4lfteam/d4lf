from src.paragon.overlay.contracts import ParagonOverlayContract
from src.paragon.overlay.popup import OverlayPopupMixin


def test_overlay_popup_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupMixin, ParagonOverlayContract)
