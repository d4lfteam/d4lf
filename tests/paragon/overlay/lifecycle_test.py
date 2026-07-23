from src.paragon.overlay.lifecycle import OverlayLifecycleMixin
from src.paragon.shared import OverlayContract


def test_overlay_lifecycle_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayLifecycleMixin, OverlayContract)
