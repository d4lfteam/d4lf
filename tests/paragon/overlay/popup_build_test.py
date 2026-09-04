from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.popup_build import OverlayPopupBuildMixin


def test_overlay_build_popup_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupBuildMixin, OverlayContract)
