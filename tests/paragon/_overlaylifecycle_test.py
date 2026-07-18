from src.paragon._overlaylifecycle import OverlayLifecycleMixin
from src.paragon._shared import OverlayContract


def test_overlay_lifecycle_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayLifecycleMixin, OverlayContract)
