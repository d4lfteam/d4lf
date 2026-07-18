from src.paragon._overlaypopup import OverlayPopupMixin
from src.paragon._shared import OverlayContract


def test_overlay_popup_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupMixin, OverlayContract)
