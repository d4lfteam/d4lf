from src.paragon._overlaycore import OverlayCoreMixin
from src.paragon._shared import OverlayContract


def test_overlay_core_is_built_on_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayCoreMixin, OverlayContract)
