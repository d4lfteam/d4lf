from src.paragon._overlaypopupmeasure import OverlayPopupMixin
from src.paragon._shared import OverlayContract


def test_overlay_popup_measurement_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupMixin, OverlayContract)
