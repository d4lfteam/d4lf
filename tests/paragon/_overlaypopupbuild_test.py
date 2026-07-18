from src.paragon._overlaypopupbuild import OverlayPopupBuildMixin
from src.paragon._shared import OverlayContract


def test_overlay_build_popup_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupBuildMixin, OverlayContract)
