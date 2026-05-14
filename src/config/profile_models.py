"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import enum
import logging
import sys

from pydantic import BaseModel, ConfigDict, RootModel, field_validator, model_validator

from src.config.helper import check_greater_than_zero, validate_percent
from src.item.data.item_type import ItemType  # noqa: TC001
from src.item.data.rarity import ItemRarity

MODULE_LOGGER = logging.getLogger(__name__)


def _parse_item_type_or_rarities(data: str | list[str]) -> list[str]:
    if isinstance(data, str):
        return [data]
    return data


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
    want_greater: bool = False
    minPercentOfAffix: int = 0

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        if name not in Dataloader().affix_dict:
            msg = f"affix {name} does not exist"
            raise ValueError(msg)
        return name

    @field_validator("minPercentOfAffix")
    @classmethod
    def percent_validator(cls, v: int) -> int:
        return validate_percent(v)

    @model_validator(mode="after")
    def value_and_percent_are_mutually_exclusive(self) -> AffixFilterModel:
        if self.value and self.minPercentOfAffix:
            msg = "value and minPercentOfAffix cannot both be set"
            raise ValueError(msg)
        return self


class AffixFilterCountModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: list[AffixFilterModel] = []
    maxCount: int = sys.maxsize
    minCount: int = 0

    @field_validator("minCount", "maxCount")
    @classmethod
    def count_validator(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @model_validator(mode="after")
    def model_validator(self) -> AffixFilterCountModel:
        # If minCount and maxCount are not set, we assume that the lengths of the count list is the only thing that matters.
        # To not show up in the model.dict() we need to remove them from the model_fields_set property
        if "minCount" not in self.model_fields_set and "maxCount" not in self.model_fields_set:
            self.minCount = len(self.count)
            self.maxCount = len(self.count)
            self.model_fields_set.remove("minCount")
            self.model_fields_set.remove("maxCount")
        if self.minCount > self.maxCount:
            msg = "minCount must be smaller than maxCount"
            raise ValueError(msg)
        if not self.count:
            msg = "count must not be empty"
            raise ValueError(msg)
        return self


class AspectUniqueFilterModel(AffixAspectFilterModel):
    minPercentOfAspect: int = 0

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

    @field_validator("minPercentOfAspect")
    @classmethod
    def percent_validator(cls, v: int) -> int:
        return validate_percent(v)

    @model_validator(mode="after")
    def value_and_percent_are_mutually_exclusive(self) -> AspectUniqueFilterModel:
        if self.value and self.minPercentOfAspect:
            msg = "value and minPercentOfAspect cannot both be set"
            raise ValueError(msg)
        return self


class GlobalUniqueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profileAlias: str = ""
    minGreaterAffixCount: int = 0
    minPercentOfAspect: int = 0
    minPower: int = 0

    @field_validator("minPower")
    @classmethod
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("minGreaterAffixCount")
    @classmethod
    def count_validator(cls, v: int) -> int:
        if not 0 <= v <= 4:
            msg = "must be in [0, 4]"
            raise ValueError(msg)
        return v

    @field_validator("minPercentOfAspect")
    @classmethod
    def percent_validator(cls, v: int) -> int:
        return validate_percent(v)


class ItemFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    affixPool: list[AffixFilterCountModel] = []
    inherentPool: list[AffixFilterCountModel] = []
    itemType: list[ItemType] = []
    minGreaterAffixCount: int = 0
    minPower: int = 0
    uniqueAspect: AspectUniqueFilterModel = None

    @field_validator("minPower")
    @classmethod
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("minGreaterAffixCount")
    @classmethod
    def min_greater_affix_in_range(cls, v: int) -> int:
        if not 0 <= v <= 4:
            msg = "must be in [0, 4]"
            raise ValueError(msg)
        return v

    @field_validator("itemType", mode="before")
    @classmethod
    def parse_item_type(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)


DynamicItemFilterModel = RootModel[dict[str, ItemFilterModel]]


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
        return _parse_item_type_or_rarities(data)


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Affixes: list[DynamicItemFilterModel] = []
    AspectUpgrades: list[str] = []
    GlobalUniques: list[GlobalUniqueModel] = []
    name: str
    Sigils: SigilFilterModel = SigilFilterModel(blacklist=[], whitelist=[], priority=SigilPriority.blacklist)
    Tributes: list[TributeFilterModel] = []
    Paragon: dict[str, object] | list[dict[str, object]] | None = None

    @model_validator(mode="before")
    def aspects_must_exist(self) -> ProfileModel:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        if "AspectUpgrades" not in self:
            return self

        all_aspects_list = Dataloader().aspect_list
        aspects_not_in_all_aspects = [x for x in self["AspectUpgrades"] if x not in all_aspects_list]
        if aspects_not_in_all_aspects:
            msg = f"The following aspects in AspectUpgrades do not exist in our data: {', '.join(aspects_not_in_all_aspects)}"
            raise ValueError(msg)

        return self
