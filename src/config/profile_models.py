"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import enum
import logging
import sys

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

from src.config.helper import check_greater_than_zero, validate_greater_affix_count, validate_percent
from src.item.data.item_type import ItemType  # noqa: TC001
from src.item.data.rarity import ItemRarity
from src.scripts import correct_name

MODULE_LOGGER = logging.getLogger(__name__)


def _parse_item_type_or_rarities(data: str | list[str]) -> list[str]:
    if isinstance(data, str):
        return [data]
    return data


def _coerce_name_rarity_filter_data(data: str | list[str] | dict[str, str | list[str]]) -> dict[str, str | list[str]]:
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


def _normalize_existing_set_name(name: str | None, field_name: str) -> str | None:
    if not name:
        return None

    # This on module level would be a circular import, so we do it lazy for now
    from src.dataloader import Dataloader  # noqa: PLC0415

    name = correct_name(name)
    if name not in Dataloader().set_list:
        msg = f"{field_name} {name} does not exist"
        raise ValueError(msg)
    return name


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
    want_greater: bool = False
    min_percent_of_affix: int = Field(default=0, alias="minPercentOfAffix")

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        if name not in Dataloader().affix_dict:
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


DynamicItemFilterModel = RootModel[dict[str, ItemFilterModel]]


class SealCharmFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    affix_pool: list[AffixFilterCountModel] = Field(default=[], alias="affixPool")
    min_greater_affix_count: int = Field(default=0, alias="minGreaterAffixCount")
    rarities: list[ItemRarity] = []

    @field_validator("min_greater_affix_count")
    @classmethod
    def min_greater_affix_in_range(cls, v: int) -> int:
        return validate_greater_affix_count(v)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)


class CharmFilterModel(SealCharmFilterModel):
    set_name: str | None = Field(default=None, alias="set")
    unique_aspect: str | None = Field(default=None, alias="uniqueAspect")

    @field_validator("set_name")
    @classmethod
    def set_must_exist(cls, name: str | None) -> str | None:
        return _normalize_existing_set_name(name, "set")

    @field_validator("unique_aspect")
    @classmethod
    def normalize_unique_aspect(cls, name: str | None) -> str | None:
        return correct_name(name)


class SealFilterModel(SealCharmFilterModel):
    boosted_set: str | None = Field(default=None, alias="boostedSet")

    @field_validator("boosted_set")
    @classmethod
    def boosted_set_must_exist(cls, name: str | None) -> str | None:
        return _normalize_existing_set_name(name, "boostedSet")


DynamicSealCharmFilterModel = RootModel[dict[str, SealCharmFilterModel]]
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
        from src.dataloader import Dataloader  # noqa: PLC0415

        names = [names_in] if isinstance(names_in, str) else names_in
        errors = [name for name in names if name not in Dataloader().affix_sigil_dict]
        if errors:
            msg = f"The following affixes/dungeons do not exist: {errors}"
            raise ValueError(msg)
        return names_in


class SigilFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blacklist: list[SigilConditionModel] = []
    priority: SigilPriority = SigilPriority.blacklist
    whitelist: list[SigilConditionModel] = []

    @model_validator(mode="after")
    def data_integrity(self) -> SigilFilterModel:
        errors = [item for item in self.blacklist if item in self.whitelist]
        if errors:
            msg = f"blacklist and whitelist must not overlap: {errors}"
            raise ValueError(msg)
        return self


class TributeFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = None
    rarities: list[ItemRarity] = []

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
        return _coerce_name_rarity_filter_data(data)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)


class NameRarityFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    rarities: list[ItemRarity] = []

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str | None) -> str | None:
        return correct_name(name)

    @model_validator(mode="before")
    @classmethod
    def parse_data(cls, data: str | list[str] | dict[str, str | list[str]]) -> dict[str, str | list[str]]:
        return _coerce_name_rarity_filter_data(data)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)


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
    paragon: dict[str, object] | list[dict[str, object]] | None = Field(default=None, alias="Paragon")

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
