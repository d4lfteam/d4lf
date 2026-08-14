import re
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.paragon import NODES_LEN
from src.profiles.validation.normalization import _as_string_keyed_dict
from src.type_aliases import YamlValue  # ruff:ignore[typing-only-first-party-import]


class ParagonBoardModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)

    name: str = Field(alias="Name")
    glyph: str = Field(default="", alias="Glyph")
    rotation: str = Field(default="0°", alias="Rotation")
    nodes: list[bool] = Field(alias="Nodes")
    board_id: str | None = Field(default=None, alias="BoardId")
    glyph_id: str | None = Field(default=None, alias="GlyphId")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, name: str) -> str:
        if not name.strip():
            msg = "Name must not be empty"
            raise ValueError(msg)
        return name

    @field_validator("rotation", mode="before")
    @classmethod
    def normalize_rotation(cls, rotation: YamlValue) -> str:
        if isinstance(rotation, int) and not isinstance(rotation, bool):
            degrees = rotation
        elif isinstance(rotation, str):
            match = re.search(r"^\s*(\d+)\s*°?\s*$", rotation)
            if not match:
                msg = "Rotation must be one of 0, 90, 180, or 270 degrees"
                raise ValueError(msg)
            degrees = int(match.group(1))
        else:
            msg = "Rotation must be an integer or string"
            raise ValueError(msg)

        if degrees not in {0, 90, 180, 270}:
            msg = "Rotation must be one of 0, 90, 180, or 270 degrees"
            raise ValueError(msg)
        return f"{degrees}°"

    @field_validator("nodes", mode="before")
    @classmethod
    def validate_nodes(cls, nodes: list[YamlValue]) -> list[YamlValue]:
        if not isinstance(nodes, list):
            msg = f"Nodes must be a list of {NODES_LEN} boolean-compatible values"
            raise ValueError(msg)
        if len(nodes) != NODES_LEN:
            msg = f"Nodes must contain exactly {NODES_LEN} values"
            raise ValueError(msg)
        return list(nodes)


class ParagonPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)

    name: str = Field(alias="Name")
    source: str | None = Field(default=None, alias="Source")
    generated_at: str | None = Field(default=None, alias="GeneratedAt")
    generator: str | None = Field(default=None, alias="Generator")
    paragon_boards_list: list[list[ParagonBoardModel]] = Field(default_factory=list, alias="ParagonBoardsList")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, name: str) -> str:
        if not name.strip():
            msg = "Name must not be empty"
            raise ValueError(msg)
        return name

    @model_validator(mode="before")
    @classmethod
    def normalize_paragon_boards_list(cls, data: YamlValue) -> YamlValue:
        data_dict = _as_string_keyed_dict(data)
        if data_dict is None:
            return data

        key = (
            "ParagonBoardsList"
            if "ParagonBoardsList" in data_dict
            else "paragon_boards_list"
            if "paragon_boards_list" in data_dict
            else None
        )
        if key is None:
            return data

        boards_list = data_dict[key]
        if not isinstance(boards_list, list):
            return data
        if not boards_list:
            msg = "ParagonBoardsList must not be empty"
            raise ValueError(msg)
        if all(not isinstance(step, list) for step in boards_list):
            normalized = dict(data_dict)
            normalized.pop(key, None)
            normalized["ParagonBoardsList"] = [boards_list]
            return cast("YamlValue", normalized)
        return data

    @model_validator(mode="after")
    def paragon_boards_list_must_not_be_empty(self) -> ParagonPayloadModel:
        if not self.paragon_boards_list or any(not step for step in self.paragon_boards_list):
            msg = "ParagonBoardsList must not be empty"
            raise ValueError(msg)
        return self
