"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import enum
import logging
import re
import sys

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    field_serializer,
    field_validator,
    model_validator,
)

from src.config.helper import check_greater_than_zero, validate_greater_affix_count, validate_percent
from src.item.data.item_type import ItemType  # noqa: TC001
from src.item.data.rarity import ItemRarity
from src.scripts import correct_name

MODULE_LOGGER = logging.getLogger(__name__)


def _parse_item_type_or_rarities(data: str | list[str]) -> list[str]:
    if isinstance(data, str):
        return [data]
    return data


def _validate_set_name(name: str | None, field_name: str) -> str | None:
    if not name:
        return None

    # This on module level would be a circular import, so we do it lazy for now
    from src.dataloader import Dataloader  # noqa: PLC0415

    name = correct_name(name)
    if name not in Dataloader().set_list:
        msg = f"{field_name} {name} does not exist"
        raise ValueError(msg)
    return name


def _normalize_rarities(data: str | list[str]) -> list[str]:
    values = [data] if isinstance(data, str) else data
    return [v.lower() if isinstance(v, str) else v for v in values]


class AffixAspectFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    value: float | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_data(cls, data: str | list[str] | list[str | float] | dict[str, str | float]) -> dict[str, str | float]:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return {"name": data}
        if isinstance(data, list):
            if not data or len(data) > 2:
                msg = "list, cannot be empty or larger than 2 items"
                raise ValueError(msg)
            result = {}
            if len(data) >= 1:
                result["name"] = data[0]
            if len(data) >= 2:
                result["value"] = data[1]
            return result
        msg = "must be str or list"
        raise ValueError(msg)


class AffixFilterModel(AffixAspectFilterModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    min_percent_of_affix: int = Field(default=0, alias="minPercentOfAffix")
    want_greater: bool = False

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        if (
            name not in Dataloader().affix_dict
            and name not in Dataloader().charm_affix_dict
            and name not in Dataloader().seal_affix_dict
        ):
            msg = f"affix {name} does not exist"
            raise ValueError(msg)
        return name

    @field_validator("min_percent_of_affix")
    @classmethod
    def percent_validator(cls, v: int) -> int:
        return validate_percent(v)

    @model_validator(mode="after")
    def value_and_percent_are_mutually_exclusive(self) -> AffixFilterModel:
        if self.value and self.min_percent_of_affix:
            msg = "value and minPercentOfAffix cannot both be set"
            raise ValueError(msg)

        return self


class AffixFilterCountModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    count: list[AffixFilterModel] = []
    max_count: int = Field(default=sys.maxsize, alias="maxCount")
    min_count: int = Field(default=0, alias="minCount")

    @field_validator("min_count", "max_count")
    @classmethod
    def count_validator(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @model_validator(mode="after")
    def model_validator(self) -> AffixFilterCountModel:
        # If minCount and maxCount are not set, we assume that the lengths of the count list is the only thing that matters.
        # To not show up in the model.dict() we need to remove them from the model_fields_set property
        if "min_count" not in self.model_fields_set and "max_count" not in self.model_fields_set:
            self.min_count = len(self.count)
            self.max_count = len(self.count)
            self.model_fields_set.remove("min_count")
            self.model_fields_set.remove("max_count")
        if self.min_count > self.max_count:
            msg = "minCount must be smaller than maxCount"
            raise ValueError(msg)
        if not self.count:
            msg = "count must not be empty"
            raise ValueError(msg)
        return self


def _validate_affix_pool_names(
    affix_pool: list[AffixFilterCountModel], valid_affixes: dict[str, str], field_name: str
) -> None:
    invalid_affix_names = sorted({
        affix.name for affix_group in affix_pool for affix in affix_group.count if affix.name not in valid_affixes
    })
    if invalid_affix_names:
        msg = f"{field_name} affix {', '.join(invalid_affix_names)} does not exist"
        raise ValueError(msg)


class AspectUniqueFilterModel(AffixAspectFilterModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    min_percent_of_aspect: int = Field(default=0, alias="minPercentOfAspect")

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        # Ensure name is in format we expect
        name = name.lower().replace("'", "").replace(" ", "_").replace(",", "")

        if name not in Dataloader().aspect_unique_dict:
            msg = f"aspect {name} does not exist"
            raise ValueError(msg)
        return name

    @field_validator("min_percent_of_aspect")
    @classmethod
    def percent_validator(cls, v: int) -> int:
        return validate_percent(v)

    @model_validator(mode="after")
    def value_and_percent_are_mutually_exclusive(self) -> AspectUniqueFilterModel:
        if self.value and self.min_percent_of_aspect:
            msg = "value and minPercentOfAspect cannot both be set"
            raise ValueError(msg)
        return self


class GlobalUniqueModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    profile_alias: str = Field(default="", alias="profileAlias")
    min_greater_affix_count: int = Field(default=0, alias="minGreaterAffixCount")
    min_percent_of_aspect: int = Field(default=0, alias="minPercentOfAspect")
    min_power: int = Field(default=0, alias="minPower")

    @field_validator("min_power")
    @classmethod
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("min_greater_affix_count")
    @classmethod
    def count_validator(cls, v: int) -> int:
        return validate_greater_affix_count(v)

    @field_validator("min_percent_of_aspect")
    @classmethod
    def percent_validator(cls, v: int) -> int:
        return validate_percent(v)


class ItemFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    affix_pool: list[AffixFilterCountModel] = Field(default=[], alias="affixPool")
    inherent_pool: list[AffixFilterCountModel] = Field(default=[], alias="inherentPool")
    item_type: list[ItemType] = Field(default=[], alias="itemType")
    min_greater_affix_count: int = Field(default=0, alias="minGreaterAffixCount")
    min_power: int = Field(default=0, alias="minPower")
    rarities: list[ItemRarity] = Field(default=[], validation_alias="rarity", serialization_alias="rarity")
    unique_aspect: list[AspectUniqueFilterModel] = Field(default=[], alias="uniqueAspect")

    @field_validator("min_power")
    @classmethod
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("min_greater_affix_count")
    @classmethod
    def min_greater_affix_in_range(cls, v: int) -> int:
        return validate_greater_affix_count(v)

    @field_validator("item_type", mode="before")
    @classmethod
    def parse_item_type(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _normalize_rarities(data)

    @field_validator("unique_aspect", mode="before")
    @classmethod
    def parse_unique_aspect(cls, data: dict | list[dict] | None) -> list[dict]:
        if not data:
            return []
        if isinstance(data, dict):
            return [data]
        return data

    @model_validator(mode="after")
    def unique_aspect_names_must_be_unique(self) -> ItemFilterModel:
        if len({aspect.name for aspect in self.unique_aspect}) != len(self.unique_aspect):
            msg = "uniqueAspect names must be unique"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def affix_names_must_match_item_pool(self) -> ItemFilterModel:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        affix_dict = Dataloader().affix_dict
        _validate_affix_pool_names(self.affix_pool, affix_dict, "affixPool")
        _validate_affix_pool_names(self.inherent_pool, affix_dict, "inherentPool")
        return self


DynamicItemFilterModel = RootModel[dict[str, ItemFilterModel]]


class _BaseSealOrCharmFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    affix_pool: list[AffixFilterCountModel] = Field(default=[], alias="affixPool")
    min_greater_affix_count: int = Field(default=0, alias="minGreaterAffixCount")
    rarities: list[ItemRarity] = Field(default=[], validation_alias="rarity", serialization_alias="rarity")
    unique_aspect: list[AspectUniqueFilterModel] = Field(default=[], alias="uniqueAspect")

    @field_validator("min_greater_affix_count")
    @classmethod
    def min_greater_affix_in_range(cls, v: int) -> int:
        return validate_greater_affix_count(v)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _normalize_rarities(data)

    @model_validator(mode="after")
    def unique_aspects_must_be_unique(self) -> _BaseSealOrCharmFilterModel:
        if len({aspect.name for aspect in self.unique_aspect}) != len(self.unique_aspect):
            msg = "uniqueAspect names must be unique"
            raise ValueError(msg)

        return self


class CharmFilterModel(_BaseSealOrCharmFilterModel):
    set: list[str] = Field(default=[], alias="set")

    @field_validator("set")
    @classmethod
    def set_must_exist(cls, sets: list[str]) -> list[str]:
        return [_validate_set_name(name, "set") for name in sets]

    @model_validator(mode="after")
    def set_and_unique_aspects_must_be_unique(self) -> CharmFilterModel:
        if len(set(self.set)) != len(self.set):
            msg = "set names must be unique"
            raise ValueError(msg)

        if self.set and self.unique_aspect:
            msg = "can't define both set and unique aspect"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def affix_names_must_match_charm_pool(self) -> CharmFilterModel:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        _validate_affix_pool_names(self.affix_pool, Dataloader().charm_affix_dict, "affixPool")
        return self


class SealFilterModel(_BaseSealOrCharmFilterModel):
    @model_validator(mode="after")
    def affix_names_must_match_seal_pool(self) -> SealFilterModel:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        _validate_affix_pool_names(self.affix_pool, Dataloader().seal_affix_dict, "affixPool")
        return self


DynamicCharmFilterModel = RootModel[dict[str, CharmFilterModel]]
DynamicSealFilterModel = RootModel[dict[str, SealFilterModel]]


class SigilPriority(enum.StrEnum):
    blacklist = enum.auto()
    whitelist = enum.auto()


class SigilConditionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    condition: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def parse_data(cls, data: str | list[str] | list[str | float] | dict[str, str | float]) -> dict[str, str | float]:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return {"name": data}
        if isinstance(data, list):
            if not data:
                msg = "list cannot be empty"
                raise ValueError(msg)
            result = {}
            if len(data) >= 1:
                result["name"] = data[0]
            if len(data) >= 2:
                result["condition"] = data[1:]
            return result
        msg = "must be str or list"
        raise ValueError(msg)

    @field_validator("condition", "name")
    @classmethod
    def name_must_exist(cls, names_in: str | list[str]) -> str | list[str]:
        # This on module level would be a circular import, so we do it lazy for now
        from src.item.sigil_rules import SigilRules  # noqa: PLC0415

        names = [names_in] if isinstance(names_in, str) else names_in
        sigil_rules = SigilRules.default()
        errors = [name for name in names if not sigil_rules.target(name).known]
        if errors:
            msg = f"The following affixes/dungeons do not exist: {errors}"
            raise ValueError(msg)
        return names_in


class SigilFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    blacklist: list[SigilConditionModel] = []
    priority: SigilPriority = SigilPriority.blacklist
    rarities: list[ItemRarity] = Field(default=[], validation_alias="rarity", serialization_alias="rarity")
    whitelist: list[SigilConditionModel] = []

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _normalize_rarities(data)

    @model_validator(mode="after")
    def data_integrity(self) -> SigilFilterModel:
        errors = [item for item in self.blacklist if item in self.whitelist]
        if errors:
            msg = f"blacklist and whitelist must not overlap: {errors}"
            raise ValueError(msg)
        return self


class TributeFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str = None
    rarities: list[ItemRarity] = Field(
        default=[], validation_alias=AliasChoices("rarity", "rarities"), serialization_alias="rarity"
    )

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        if not name:
            return name

        tribute_dict = Dataloader().tribute_dict
        # Allow people to shorthand and leave off "tribute_of_"
        name_with_tribute = "tribute_of_" + name
        if name not in tribute_dict and name_with_tribute not in tribute_dict:
            msg = f"No tribute named {name} or {name_with_tribute} exists"
            raise ValueError(msg)

        if name_with_tribute in tribute_dict:
            name = name_with_tribute

        return name

    @model_validator(mode="before")
    @classmethod
    def parse_data(cls, data: str | list[str] | dict[str, str | list[str]]) -> dict[str, str | list[str]]:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            if any(rarity.value.lower() == data.lower() for rarity in ItemRarity):
                return {"rarities": [data]}
            return {"name": data}
        if isinstance(data, list):
            if not data:
                msg = "list cannot be empty"
                raise ValueError(msg)
            return {"rarities": data}
        msg = "must be str or list"
        raise ValueError(msg)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _normalize_rarities(data)


class ParagonBoardModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

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
    def normalize_rotation(cls, rotation: object) -> str:
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
    def validate_nodes(cls, nodes: object) -> list[object]:
        if not isinstance(nodes, list):
            msg = "Nodes must be a list of 441 boolean-compatible values"
            raise ValueError(msg)
        if len(nodes) != 441:
            msg = "Nodes must contain exactly 441 values"
            raise ValueError(msg)
        return nodes


class ParagonPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

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
    def normalize_paragon_boards_list(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        key = (
            "ParagonBoardsList"
            if "ParagonBoardsList" in data
            else "paragon_boards_list"
            if "paragon_boards_list" in data
            else None
        )
        if key is None:
            return data

        boards_list = data[key]
        if not isinstance(boards_list, list):
            return data
        if not boards_list:
            msg = "ParagonBoardsList must not be empty"
            raise ValueError(msg)
        if all(not isinstance(step, list) for step in boards_list):
            normalized = dict(data)
            normalized.pop(key, None)
            normalized["ParagonBoardsList"] = [boards_list]
            return normalized
        return data

    @model_validator(mode="after")
    def paragon_boards_list_must_not_be_empty(self) -> ParagonPayloadModel:
        if not self.paragon_boards_list or any(not step for step in self.paragon_boards_list):
            msg = "ParagonBoardsList must not be empty"
            raise ValueError(msg)
        return self


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    affixes: list[DynamicItemFilterModel] = Field(default=[], alias="Affixes")
    aspect_upgrades: list[str] = Field(default=[], alias="AspectUpgrades")
    charms: list[DynamicCharmFilterModel] = Field(default=[], alias="Charms")
    global_uniques: list[GlobalUniqueModel] = Field(default=[], alias="GlobalUniques")
    name: str
    seals: list[DynamicSealFilterModel] = Field(default=[], alias="Seals")
    sigils: SigilFilterModel = Field(
        default=SigilFilterModel(blacklist=[], whitelist=[], priority=SigilPriority.blacklist), alias="Sigils"
    )
    tributes: list[TributeFilterModel] = Field(default=[], alias="Tributes")
    paragon: ParagonPayloadModel | None = Field(default=None, alias="Paragon")

    @model_validator(mode="before")
    def aspects_must_exist(self) -> ProfileModel:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        # Check both snake_case and camelCase (alias) keys
        aspect_key = "aspect_upgrades" if "aspect_upgrades" in self else "AspectUpgrades"
        if aspect_key not in self:
            return self

        all_aspects_list = Dataloader().aspect_list
        aspects_not_in_all_aspects = [x for x in self[aspect_key] if x not in all_aspects_list]
        if aspects_not_in_all_aspects:
            msg = f"The following aspects in AspectUpgrades do not exist in our data: {', '.join(aspects_not_in_all_aspects)}"
            raise ValueError(msg)

        return self

    @model_validator(mode="before")
    @classmethod
    def normalize_paragon(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        key = "Paragon" if "Paragon" in data else "paragon" if "paragon" in data else None
        if key is None:
            return data

        paragon = data[key]
        if paragon is None:
            return data
        if not isinstance(paragon, list):
            return data
        if not paragon:
            return {**data, key: None}
        if len(paragon) > 1:
            msg = "Paragon must contain at most one payload"
            raise ValueError(msg)
        if not isinstance(paragon[0], dict):
            msg = "Paragon legacy list entries must be objects"
            raise ValueError(msg)
        return {**data, key: paragon[0]}

    @field_serializer("paragon", when_used="json-unless-none")
    def serialize_paragon(self, paragon: ParagonPayloadModel | None) -> object:
        if paragon is None:
            return None
        return paragon.model_dump(mode="python", by_alias=True, exclude_none=True, exclude_defaults=True)
