from src.paragon.overlay.popup import OverlayPopupMixin
from src.paragon.shared import OverlayContract


def test_overlay_popup_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupMixin, OverlayContract)
