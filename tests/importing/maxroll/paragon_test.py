from typing import cast

import pytest

from src.importing.maxroll.paragon import extract_maxroll_paragon_steps


def test_maxroll_paragon_extractor_returns_empty_for_missing_data() -> None:
    assert extract_maxroll_paragon_steps({}, {}) == []


@pytest.mark.parametrize(("rotation", "expected_index"), [(0, 5), (1, 125), (2, 435), (3, 315)])
def test_extract_maxroll_paragon_steps_keeps_rotation_index_mapping(rotation: int, expected_index: int) -> None:
    steps = extract_maxroll_paragon_steps(
        active_profile={
            "paragon": {
                "steps": [{"data": [{"id": "Paragon_Barb_00", "glyph": "", "rotation": rotation, "nodes": {"5": 1}}]}]
            }
        },
        mapping_data={"paragonBoards": {"Paragon_Barb_00": {"name": "Starting Board"}}, "paragonGlyphs": {}},
    )

    board = steps[0][0]
    assert board["Rotation"] in {"0°", "90°", "180°", "270°"}
    nodes = cast("list[bool]", board["Nodes"])
    assert nodes.count(True) == 1
    assert nodes[expected_index] is True
