import os
import typing

import pytest

from src.dataloader import Dataloader
from src.importing import ImportOptions, ImportRequest
from src.importing.infinitybuilds import import_infinitybuilds
from src.importing.paragon_export import (
    InfinityBuildsParagonCatalog,
    extract_infinitybuilds_paragon_steps,
    fetch_infinitybuilds_paragon_catalog,
)

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
URLS = ["https://infinitybuilds.gg/en/builds/barbarian-fL8P6vVSqI"]


def _request(
    *,
    url: str,
    import_aspect_upgrades: bool = True,
    add_to_profiles: bool = False,
    import_greater_affixes: bool = False,
    require_greater_affixes: bool = False,
    custom_file_name: str | None = None,
) -> ImportRequest:
    return ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=import_aspect_upgrades,
            add_to_profiles=add_to_profiles,
            import_greater_affixes=import_greater_affixes,
            require_greater_affixes=require_greater_affixes,
            custom_file_name=custom_file_name,
        ),
    )


def test_extract_infinitybuilds_paragon_steps_groups_boards_transforms_nodes_and_resolves_names() -> None:
    data = {
        "slots": [{"boardId": "paragon-board::paragon-barb-10", "rotation": 1}],
        "glyphs": {"paragon-board::paragon-barb-00::136": "glyph::rare-016-dexterity-side"},
        "activeNodes": [
            "paragon-board::paragon-barb-00::10",
            "paragon-board::paragon-barb-00::136",
            "paragon-board::paragon-barb-10::5",
        ],
    }
    catalog = InfinityBuildsParagonCatalog(
        board_labels={"paragon-board::paragon-barb-00": "Start", "paragon-board::paragon-barb-10": "Force of Nature"},
        glyph_labels={"glyph::rare-016-dexterity-side": "Exploit"},
    )
    boards = extract_infinitybuilds_paragon_steps(data, catalog, "barbarian")[0]
    assert [board["BoardId"] for board in boards] == [
        "paragon-board::paragon-barb-00",
        "paragon-board::paragon-barb-10",
    ]
    assert boards[0]["Name"] == "barbarian-start"
    assert boards[0]["Rotation"] == "0°"
    assert boards[0]["Glyph"] == "barbarian-exploit"
    assert boards[0]["Nodes"].count(True) == 2
    assert boards[0]["Nodes"][10] is True
    assert boards[0]["Nodes"][136] is True
    assert boards[1]["Name"] == "barbarian-force-of-nature"
    assert boards[1]["Rotation"] == "90°"
    assert boards[1]["GlyphId"] is None
    assert boards[1]["Nodes"][125] is True


def test_extract_infinitybuilds_paragon_steps_falls_back_to_raw_id_slug_when_catalog_misses() -> None:
    catalog = InfinityBuildsParagonCatalog(board_labels={}, glyph_labels={})
    steps = extract_infinitybuilds_paragon_steps(
        {"slots": [], "glyphs": {}, "activeNodes": ["paragon-board::paragon-unknown-99::0"]}, catalog, "barbarian"
    )
    assert steps[0][0]["Name"] == "barbarian-paragon-board-paragon-unknown-99"
    assert steps[0][0]["BoardId"] == "paragon-board::paragon-unknown-99"


def test_extract_infinitybuilds_paragon_steps_returns_empty_when_no_active_nodes() -> None:
    assert (
        extract_infinitybuilds_paragon_steps(
            {}, InfinityBuildsParagonCatalog(board_labels={}, glyph_labels={}), "barbarian"
        )
        == []
    )


@pytest.mark.parametrize(("rotation", "expected_index"), [(0, 5), (1, 125), (2, 435), (3, 315)])
def test_extract_infinitybuilds_paragon_steps_keeps_rotation_index_mapping(rotation: int, expected_index: int) -> None:
    data = {
        "slots": [{"boardId": "paragon-board::paragon-barb-10", "rotation": rotation}],
        "glyphs": {},
        "activeNodes": ["paragon-board::paragon-barb-10::5"],
    }
    catalog = InfinityBuildsParagonCatalog(
        board_labels={"paragon-board::paragon-barb-10": "Force of Nature"}, glyph_labels={}
    )
    board = extract_infinitybuilds_paragon_steps(data, catalog, "barbarian")[0][0]
    assert board["Rotation"] in {"0°", "90°", "180°", "270°"}
    assert board["Nodes"].count(True) == 1
    assert board["Nodes"][expected_index] is True


def test_fetch_infinitybuilds_paragon_catalog_builds_label_maps_from_both_datasets(mocker: MockerFixture) -> None:
    boards_response = mocker.Mock()
    boards_response.json.return_value = {
        "paragon": {"boards": [{"id": "paragon-board::paragon-barb-00", "label": "Start"}]}
    }
    glyphs_response = mocker.Mock()
    glyphs_response.json.return_value = {
        "paragon": {"glyphs": [{"id": "glyph::rare-016-dexterity-side", "label": "Exploit"}]}
    }
    get_with_retry = mocker.patch(
        "src.importing.paragon_export.get_with_retry", side_effect=[boards_response, glyphs_response]
    )
    catalog = fetch_infinitybuilds_paragon_catalog()
    assert get_with_retry.call_args_list[0][0][0].endswith("paragon-boards.json")
    assert get_with_retry.call_args_list[1][0][0].endswith("glyphs.json")
    assert catalog.board_labels == {"paragon-board::paragon-barb-00": "Start"}
    assert catalog.glyph_labels == {"glyph::rare-016-dexterity-side": "Exploit"}


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_infinitybuilds(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()
    mocker.patch("builtins.open", new=mocker.mock_open())
    import_infinitybuilds(
        request=_request(
            url=url,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            custom_file_name=None,
        )
    )
