from typing import TYPE_CHECKING

import pytest

from src.importing.d2core.catalog import CatalogStore, CatalogTransport
from src.importing.d2core.paragon import _rotate_index, normalize_paragon

if TYPE_CHECKING:
    from src.type_aliases import JsonObject, JsonValue


def test_paragon_rotation_is_clockwise_on_a_21_by_21_grid() -> None:
    assert _rotate_index(0, 0, 0) == 0
    assert _rotate_index(0, 0, 1) == 20
    assert _rotate_index(0, 0, 2) == 440
    assert _rotate_index(0, 0, 3) == 420


def _normalize_single_board(rotate: JsonValue) -> JsonObject:
    catalogs = CatalogStore(version="test", transport=CatalogTransport())
    catalogs.data["paragon"] = {"Barbarian": {"board": {"b": {"name": "Start", "data": ["n,x"]}}, "glyph": {}}}
    raw_variant: JsonObject = {"paragon": {"b": {"data": ["0_0_n"], "rotate": rotate}}}
    [[board]] = normalize_paragon(
        raw_variant, class_name="Barbarian", variant_name="v", catalogs=catalogs, warn=lambda *_args: None
    )
    return board


@pytest.mark.parametrize("rotate", [-1.5, 1.5, 0.5])
def test_fractional_rotation_is_treated_as_unrotated(rotate: float) -> None:
    board = _normalize_single_board(rotate)

    assert board["Rotation"] == "0°"
    nodes = board["Nodes"]
    assert isinstance(nodes, list)
    assert nodes[0] is True


def test_integral_rotation_is_applied() -> None:
    board = _normalize_single_board(1)

    assert board["Rotation"] == "90°"
    nodes = board["Nodes"]
    assert isinstance(nodes, list)
    assert nodes[20] is True
