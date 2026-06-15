from __future__ import annotations

import sys

import pytest

if sys.platform == "darwin":
    pytest.skip("Windows-only overlay test", allow_module_level=True)

from src.config.profile_models import ParagonPayloadModel
from src.paragon_overlay import format_board_display_text, load_builds_from_path


def test_load_builds_from_path_uses_typed_paragon_payloads(monkeypatch):
    payload = ParagonPayloadModel.model_validate({
        "Name": "Build Name",
        "ParagonBoardsList": [
            [{"Name": "Starting Board", "Glyph": "glyph_name", "Rotation": 0, "Nodes": [False] * 441}],
            [{"Name": "Second Step Board", "Glyph": "glyph_name", "Rotation": 90, "Nodes": [False] * 441}],
        ],
    })

    monkeypatch.setattr("src.item.filter.Filter.get_paragon_filters", lambda _self: {"profile_name": payload})

    builds = load_builds_from_path()

    assert [build["name"] for build in builds] == ["Build Name - Step 2", "Build Name - Step 1"]
    assert builds[0]["boards"][0].rotation == "90°"
    assert builds[1]["boards"][0].rotation == "0°"
    assert (
        format_board_display_text(builds[0]["boards"][0]) == "Second Step Board - Second Step Board - Glyph Name - 90°"
    )
