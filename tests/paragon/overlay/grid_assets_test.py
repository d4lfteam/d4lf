from src.paragon.overlay.contracts import OverlayContract
from src.paragon.overlay.grid_assets import OverlayGridMixin


def test_overlay_grid_assets_uses_the_shared_overlay_contract() -> None:
    assert issubclass(OverlayGridMixin, OverlayContract)
