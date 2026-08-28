from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.popup_measure import OverlayPopupMixin


def test_overlay_popup_measurement_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayPopupMixin, OverlayContract)
