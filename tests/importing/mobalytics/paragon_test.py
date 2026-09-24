from typing import cast

from src.importing.mobalytics.paragon import extract_mobalytics_paragon_steps


def test_mobalytics_paragon_extractor_returns_empty_for_missing_data() -> None:
    assert extract_mobalytics_paragon_steps({}) == []


def test_mobalytics_starting_board_keeps_original_node_slug_prefix() -> None:
    steps = extract_mobalytics_paragon_steps({
        "boards": [{"board": {"slug": "rogue-starter-board"}, "glyph": {"slug": "rogue-versatility"}, "rotation": 0}],
        "nodes": [{"slug": "rogue-starter-board-x11-y14"}],
    })

    board = steps[0][0]
    assert board["Name"] == "rogue-starting-board"
    assert sum(cast("list[bool]", board["Nodes"])) == 1
