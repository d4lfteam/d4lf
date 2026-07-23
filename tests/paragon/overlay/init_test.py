from src.paragon.overlay import ParagonOverlay, request_close


def test_overlay_interface_exposes_controller() -> None:
    assert ParagonOverlay is not None
    assert callable(request_close)
