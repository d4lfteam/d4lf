from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

import src.loot.highlighting as highlighting_module
from src.loot.highlighting import HighlightingVisionMode


def _slots(*centers: tuple[int, int]) -> list[SimpleNamespace]:
    return [SimpleNamespace(center=center) for center in centers]


def _inventory(occupied: tuple[int, int], empty: tuple[int, int]) -> SimpleNamespace:
    return SimpleNamespace(get_item_slots=lambda _img: (_slots(occupied), _slots(empty)))


def _patch_environment(monkeypatch) -> tuple[Mock, Mock, Mock, Mock]:
    overlay = Mock()
    create = Mock(return_value=overlay)
    worker_cls = Mock()
    publisher = Mock()
    monkeypatch.setattr(highlighting_module.HighlightingOverlay, "create", create)
    monkeypatch.setattr(highlighting_module, "HighlightingWorker", worker_cls)
    monkeypatch.setattr(highlighting_module, "Publisher", Mock(return_value=publisher))
    monkeypatch.setattr(highlighting_module, "game_window_roi", lambda: {"left": 5, "top": 6, "height": 1000})
    monkeypatch.setattr(highlighting_module, "capture", Mock())
    monkeypatch.setattr(highlighting_module, "character_inventory", lambda: _inventory((1, 1), (2, 2)))
    monkeypatch.setattr(highlighting_module, "stash_inventory", lambda: _inventory((3, 3), (4, 4)))
    monkeypatch.setattr(highlighting_module, "vendor_inventory", lambda: _inventory((5, 5), (6, 6)))
    monkeypatch.setattr(
        highlighting_module,
        "get_ui_coordinates",
        lambda: SimpleNamespace(pos=SimpleNamespace(possible_centers=[(9, 9)])),
    )
    return overlay, create, worker_cls, publisher


def test_mode_wires_overlay_and_worker_with_slot_centers(monkeypatch) -> None:
    overlay, create, worker_cls, _ = _patch_environment(monkeypatch)

    mode = HighlightingVisionMode()

    create.assert_called_once_with(4, (5, 6))
    worker_overlay, centers, vendor_centers = worker_cls.call_args.args
    assert worker_overlay is overlay is mode.overlay
    np.testing.assert_array_equal(centers, [(1, 1), (2, 2), (9, 9), (3, 3), (4, 4)])
    np.testing.assert_array_equal(vendor_centers, [(1, 1), (2, 2), (9, 9), (5, 5), (6, 6)])


def test_start_and_stop_subscribe_worker_and_clear_overlay(monkeypatch) -> None:
    overlay, _, worker_cls, publisher = _patch_environment(monkeypatch)
    mode = HighlightingVisionMode()
    worker = worker_cls.return_value

    mode.start()
    assert mode.running()
    publisher.subscribe_item.assert_called_once_with(worker.on_tts)

    mode.stop()
    assert not mode.running()
    overlay.clear.assert_called_once_with()
    worker.stop.assert_called_once_with()
    publisher.unsubscribe_item.assert_called_once_with(worker.on_tts)
