from src.paragon.overlay.popup_build import OverlayPopupBuildMixin
from src.paragon.shared import OverlayContract


def test_overlay_build_popup_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupBuildMixin, OverlayContract)
