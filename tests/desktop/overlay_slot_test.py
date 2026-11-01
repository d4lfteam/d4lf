from src.desktop.overlay_slot import OverlaySlot


def test_slot_stores_and_clears_overlay_instance() -> None:
    slot: OverlaySlot[object] = OverlaySlot()
    marker = object()
    slot.set(marker)

    assert slot.get() is marker
    assert slot.is_open()

    slot.clear(marker)

    assert slot.get() is None
    assert not slot.is_open()


def test_slot_does_not_clear_a_replacement_overlay() -> None:
    slot: OverlaySlot[object] = OverlaySlot()
    first = object()
    second = object()
    slot.set(first)
    slot.set(second)

    slot.clear(first)
    assert slot.get() is second

    slot.clear()
    assert slot.get() is None


def test_slot_close_request_is_reset_when_published() -> None:
    slot: OverlaySlot[object] = OverlaySlot()
    slot.request_close()
    assert slot.close_requested.is_set()

    slot.set(object())
    assert not slot.close_requested.is_set()
