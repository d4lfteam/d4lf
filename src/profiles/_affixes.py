import sys

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.config.helper import check_greater_than_zero, validate_greater_affix_count, validate_percent


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
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
    min_percent_of_affix: int = Field(default=0, alias="minPercentOfAffix")
    want_greater: bool = False

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # ruff:ignore[import-outside-top-level]

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
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
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
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
    min_percent_of_aspect: int = Field(default=0, alias="minPercentOfAspect")

    @field_validator("name")
    @classmethod
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # ruff:ignore[import-outside-top-level]

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
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
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
