from src.overlay import state


def test_state_stores_and_clears_overlay_instance() -> None:
    marker = object()
    state.set_overlay(marker)

    assert state.get_overlay() is marker
    assert state.is_open()

    state.clear_overlay(marker)

    assert state.get_overlay() is None
    assert not state.is_open()


def test_state_does_not_clear_a_replacement_overlay() -> None:
    first = object()
    second = object()
    state.set_overlay(first)
    state.set_overlay(second)

    state.clear_overlay(first)

    assert state.get_overlay() is second
    state.clear_overlay(second)
