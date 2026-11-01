from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

import src.loot.highlighting as highlighting_module
from src.loot.highlighting import create_highlighting_vision_mode


def _slots(*centers: tuple[int, int]) -> list[SimpleNamespace]:
    return [SimpleNamespace(center=center) for center in centers]


def _inventory(occupied: tuple[int, int], empty: tuple[int, int]) -> SimpleNamespace:
    return SimpleNamespace(get_item_slots=lambda _img: (_slots(occupied), _slots(empty)))


def _patch_environment(monkeypatch) -> tuple[Mock, Mock, Mock]:
    root, canvas = Mock(), Mock()
    create_on_ui_thread = Mock(side_effect=lambda create: create(root, canvas))
    monkeypatch.setattr(highlighting_module, "create_on_ui_thread", create_on_ui_thread)
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
    return root, canvas, create_on_ui_thread


def test_creation_wires_window_geometry_and_slot_centers_into_the_worker(monkeypatch) -> None:
    root, canvas, create_on_ui_thread = _patch_environment(monkeypatch)

    mode = create_highlighting_vision_mode()

    create_on_ui_thread.assert_called_once()
    assert mode.root is root
    assert mode.canvas is canvas
    assert mode.thick == 4
    assert mode.screen_offset == (5, 6)
    np.testing.assert_array_equal(mode.worker._possible_centers, [(1, 1), (2, 2), (9, 9), (3, 3), (4, 4)])
    np.testing.assert_array_equal(mode.worker._possible_vendor_centers, [(1, 1), (2, 2), (9, 9), (5, 5), (6, 6)])
