from src.overlay.widget import BossTimerOverlay


def test_widget_interface_exposes_overlay() -> None:
    assert BossTimerOverlay is not None
