import pytest

from src.paragon_transform import (
    GRID,
    NODES_LEN,
    class_slug_from_name,
    nodes_to_grid,
    parse_rotation,
    prefix_with_class_slug,
    rotation_info_degrees,
    rotation_info_quarter_turn,
    slugify,
    transform_flat_index,
    transform_xy,
)


@pytest.mark.parametrize(("loc", "rotation", "expected"), [(5, 0, 5), (5, 1, 125), (5, 2, 435), (5, 3, 315)])
def test_transform_flat_index_rotates_all_quarter_turns(loc: int, rotation: int, expected: int) -> None:
    assert transform_flat_index(loc=loc, rotation=rotation) == expected


@pytest.mark.parametrize(("rotation_deg", "expected"), [(0, 30), (90, 208), (180, 410), (270, 232)])
def test_transform_xy_matches_d4builds_rotation_mapping(rotation_deg: int, expected: int) -> None:
    assert transform_xy(x=10, y=2, rotation_deg=rotation_deg, base="d4builds") == expected


@pytest.mark.parametrize(("rotation_deg", "expected"), [(0, 283), (90, 217), (180, 157), (270, 223)])
def test_transform_xy_matches_mobalytics_rotation_mapping(rotation_deg: int, expected: int) -> None:
    assert transform_xy(x=11, y=14, rotation_deg=rotation_deg, base="mobalytics") == expected


def test_nodes_to_grid_reshapes_flat_nodes_using_shared_grid_size() -> None:
    nodes = [False] * NODES_LEN
    nodes[0] = True
    nodes[GRID - 1] = True
    nodes[GRID] = True
    nodes[NODES_LEN - 1] = True

    grid = nodes_to_grid(nodes)

    assert len(grid) == GRID
    assert len(grid[0]) == GRID
    assert grid[0][0] is True
    assert grid[0][GRID - 1] is True
    assert grid[1][0] is True
    assert grid[GRID - 1][GRID - 1] is True


@pytest.mark.parametrize("rotation_deg", [0, 90, 180, 270])
def test_rotation_degrees_round_trips_through_parse(rotation_deg: int) -> None:
    assert parse_rotation(rotation_info_degrees(rotation_deg)) == rotation_deg


def test_rotation_fallback_formats_unknown_as_question_mark() -> None:
    assert rotation_info_degrees(45) == "?°"
    assert parse_rotation("?°") == 0


def test_rotation_quarter_turn_formats_supported_values() -> None:
    assert [rotation_info_quarter_turn(rot) for rot in (0, 1, 2, 3)] == ["0°", "90°", "180°", "270°"]


def test_slug_helpers_cover_generic_class_prefix_behavior() -> None:
    assert slugify("  Force of Nature!  ") == "force-of-nature"
    assert class_slug_from_name(" Spirit Born ") == "spirit-born"
    assert prefix_with_class_slug("force-of-nature", "barbarian") == "barbarian-force-of-nature"
    assert prefix_with_class_slug("barbarian-force-of-nature", "barbarian") == "barbarian-force-of-nature"
