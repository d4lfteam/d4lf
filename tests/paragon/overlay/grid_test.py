from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.grid import OverlayGridMixin


def test_overlay_grid_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayGridMixin, OverlayContract)
