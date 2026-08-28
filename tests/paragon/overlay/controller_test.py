from typing import TYPE_CHECKING, cast

import src.paragon.overlay.controller as overlay_module
import src.paragon.overlay.state as overlay_state
from src.paragon.overlay import format_board_display_text, load_builds_from_path, request_close
from src.profiles import ParagonPayloadModel

if TYPE_CHECKING:
    from src.paragon.overlay.controller import ParagonOverlay


def test_load_builds_from_path_uses_typed_paragon_payloads(monkeypatch) -> None:
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


def test_request_close_dispatches_to_overlay_ui_thread(monkeypatch) -> None:
    class FakeOverlay:
        closed = False

        def close(self) -> None:
            self.closed = True

    overlay = FakeOverlay()
    callbacks = []
    overlay_state.set_overlay(cast("ParagonOverlay", overlay))
    monkeypatch.setattr(overlay_module, "is_alive", lambda value: value is overlay)
    monkeypatch.setattr(overlay_module, "post_to_ui_thread", callbacks.append)

    request_close()

    assert len(callbacks) == 1
    callbacks[0]()
    assert overlay.closed
    overlay_state.close_requested().clear()
    overlay_state.clear_overlay(cast("ParagonOverlay", overlay))


def test_request_close_without_an_open_overlay_is_a_no_op(monkeypatch) -> None:
    callbacks = []
    overlay_state.clear_overlay()
    monkeypatch.setattr(overlay_module, "post_to_ui_thread", callbacks.append)

    request_close()

    assert callbacks == []
