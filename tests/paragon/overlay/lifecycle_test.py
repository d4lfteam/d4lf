from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.lifecycle import OverlayLifecycleMixin


def test_overlay_lifecycle_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayLifecycleMixin, OverlayContract)
