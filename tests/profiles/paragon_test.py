import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from src.paragon import NODES_LEN
from src.profiles import ParagonBoardModel, ParagonPayloadModel, ProfileModel

if TYPE_CHECKING:
    from src.type_aliases import JsonValue

"""Comprehensive tests for pydantic models including dual naming support.

This file contains:
1. Integration tests for ProfileModel (sigils, uniques, general profiles)
2. Comprehensive unit tests for dual naming support (camelCase and snake_case)
   - Both naming conventions work for input
   - Export works correctly with by_alias parameter
   - Mixed naming in same input works
   - All validators work with both naming styles
"""


class TestParagonModels:
    @staticmethod
    def _board_data(**overrides: JsonValue) -> dict[str, JsonValue]:
        board = {
            "Name": "Starting Board",
            "Glyph": "glyph_name",
            "Rotation": 90,
            "Nodes": [False] * NODES_LEN,
            "BoardId": "Paragon_Barb_00",
            "GlyphId": "glyph_1",
        }
        board.update(overrides)
        return board

    def test_board_accepts_supported_rotations(self) -> None:
        board = ParagonBoardModel.model_validate(self._board_data(Rotation="180°"))
        assert board.rotation == "180°"

    def test_board_rejects_unsupported_rotation(self) -> None:
        with pytest.raises(ValidationError, match="Rotation must be one of 0, 90, 180, or 270 degrees"):
            ParagonBoardModel.model_validate(self._board_data(Rotation=45))

    @pytest.mark.parametrize("rotation", [360, "360°", -90])
    def test_board_rejects_wrapped_rotation_values(self, rotation: JsonValue) -> None:
        with pytest.raises(ValidationError, match="Rotation must be one of 0, 90, 180, or 270 degrees"):
            ParagonBoardModel.model_validate(self._board_data(Rotation=rotation))

    def test_board_requires_name(self) -> None:
        with pytest.raises(ValidationError, match="Name must not be empty"):
            ParagonBoardModel.model_validate(self._board_data(Name="   "))

    def test_board_requires_nodes(self) -> None:
        board_data = self._board_data()
        board_data.pop("Nodes")

        with pytest.raises(ValidationError):
            ParagonBoardModel.model_validate(board_data)

    def test_board_requires_exactly_shared_nodes_len(self) -> None:
        with pytest.raises(ValidationError, match=f"Nodes must contain exactly {NODES_LEN} values"):
            ParagonBoardModel.model_validate(self._board_data(Nodes=[False] * (NODES_LEN - 1)))

        with pytest.raises(ValidationError, match=f"Nodes must contain exactly {NODES_LEN} values"):
            ParagonBoardModel.model_validate(self._board_data(Nodes=[False] * (NODES_LEN + 1)))

    def test_all_false_nodes_are_valid(self) -> None:
        board = ParagonBoardModel.model_validate(self._board_data(Nodes=[False] * NODES_LEN))
        assert board.nodes == [False] * NODES_LEN

    def test_payload_direct_board_list_normalizes_to_one_step(self) -> None:
        payload = ParagonPayloadModel.model_validate({"Name": "Build Name", "ParagonBoardsList": [self._board_data()]})
        assert payload.paragon_boards_list == [[ParagonBoardModel.model_validate(self._board_data())]]

    def test_empty_payload_board_list_rejected(self) -> None:
        with pytest.raises(ValidationError, match="ParagonBoardsList must not be empty"):
            ParagonPayloadModel.model_validate({"Name": "Build Name", "ParagonBoardsList": []})

    def test_empty_step_in_payload_board_list_rejected(self) -> None:
        with pytest.raises(ValidationError, match="ParagonBoardsList must not be empty"):
            ParagonPayloadModel.model_validate({"Name": "Build Name", "ParagonBoardsList": [[]]})

    def test_payload_requires_name(self) -> None:
        with pytest.raises(ValidationError):
            ParagonPayloadModel.model_validate({"ParagonBoardsList": [self._board_data()]})

    def test_payload_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ParagonPayloadModel.model_validate({
                "Name": "Build Name",
                "ParagonBoardsList": [[self._board_data(UnknownField=True)]],
                "UnknownField": True,
            })

    def test_board_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            ParagonBoardModel.model_validate(self._board_data(UnknownField=True))

    def test_payload_accepts_board_and_glyph_ids(self) -> None:
        payload = ParagonPayloadModel.model_validate({
            "Name": "Build Name",
            "Source": "https://example.invalid",
            "GeneratedAt": "2026-06-15 00:00:00 UTC",
            "Generator": "d4lf v0.0.0",
            "ParagonBoardsList": [self._board_data()],
        })

        assert payload.paragon_boards_list[0][0].board_id == "Paragon_Barb_00"
        assert payload.paragon_boards_list[0][0].glyph_id == "glyph_1"

    def test_canonical_profile_paragon_payload_is_typed(self) -> None:
        profile = ProfileModel(name="test", Paragon={"Name": "Build Name", "ParagonBoardsList": [self._board_data()]})

        assert isinstance(profile.paragon, ParagonPayloadModel)
        assert profile.paragon.name == "Build Name"

    def test_legacy_empty_paragon_list_normalizes_to_none(self) -> None:
        profile = ProfileModel.model_validate({"name": "test", "Paragon": []})
        assert profile.paragon is None

    def test_legacy_single_payload_list_normalizes_to_one_payload(self) -> None:
        profile = ProfileModel.model_validate({
            "name": "test",
            "Paragon": [{"Name": "Build Name", "ParagonBoardsList": [self._board_data()]}],
        })
        assert profile.paragon is not None
        assert profile.paragon.name == "Build Name"
        assert len(profile.paragon.paragon_boards_list) == 1

    def test_legacy_multi_payload_list_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Paragon must contain at most one payload"):
            ProfileModel.model_validate({
                "name": "test",
                "Paragon": [
                    {"Name": "Build One", "ParagonBoardsList": [self._board_data()]},
                    {"Name": "Build Two", "ParagonBoardsList": [self._board_data()]},
                ],
            })

    def test_profile_serialization_preserves_paragon_aliases(self) -> None:
        profile = ProfileModel.model_validate({
            "name": "test",
            "Paragon": [
                {
                    "Name": "Build Name",
                    "Source": "https://example.invalid",
                    "Generator": "d4lf v0.0.0",
                    "GeneratedAt": "2026-06-15 00:00:00 UTC",
                    "ParagonBoardsList": [self._board_data()],
                }
            ],
        })

        exported = json.loads(profile.model_dump_json(by_alias=True))
        assert exported["Paragon"]["Name"] == "Build Name"
        assert exported["Paragon"]["ParagonBoardsList"][0][0]["Name"] == "Starting Board"
        assert exported["Paragon"]["ParagonBoardsList"][0][0]["Rotation"] == "90°"
        assert len(exported["Paragon"]["ParagonBoardsList"][0][0]["Nodes"]) == NODES_LEN

    def test_serialize_paragon_excludes_null_metadata(self) -> None:
        profile = ProfileModel(name="test", Paragon={"Name": "Build Name", "ParagonBoardsList": [self._board_data()]})

        exported = json.loads(profile.model_dump_json(by_alias=True))
        paragon = exported["Paragon"]
        assert "Source" not in paragon
        assert "GeneratedAt" not in paragon
        assert "Generator" not in paragon
