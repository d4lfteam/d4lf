from src.paragon.overlay.contracts import ParagonOverlayContract
from src.paragon.overlay.grid import OverlayGridMixin


def test_overlay_grid_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayGridMixin, ParagonOverlayContract)
