from src.paragon._overlaygrid import OverlayGridMixin
from src.paragon._shared import OverlayContract


def test_overlay_grid_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayGridMixin, OverlayContract)
