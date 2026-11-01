from src.paragon.overlay.contracts import ParagonOverlayContract
from src.paragon.overlay.core import OverlayCoreMixin


def test_overlay_core_is_built_on_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayCoreMixin, ParagonOverlayContract)
