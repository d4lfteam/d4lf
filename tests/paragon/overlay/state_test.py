from typing import TYPE_CHECKING, cast

from src.paragon.overlay import state

if TYPE_CHECKING:
    from src.paragon.overlay.controller import ParagonOverlay


def test_overlay_state_publishes_and_clears_the_active_overlay() -> None:
    first = object()
    second = object()

    state.set_overlay(cast("ParagonOverlay", first))
    state.set_overlay(cast("ParagonOverlay", second))
    state.clear_overlay(cast("ParagonOverlay", first))
    assert state.get_overlay() is second

    state.clear_overlay(cast("ParagonOverlay", second))
    assert state.get_overlay() is None


def test_overlay_state_close_request_is_reset_when_published() -> None:
    state.request_close()
    assert state.close_requested().is_set()

    state.set_overlay(cast("ParagonOverlay", object()))
    assert not state.close_requested().is_set()
    state.clear_overlay()
