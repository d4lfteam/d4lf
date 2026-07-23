from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

from src.item import ItemRarity, ItemType  # ruff:ignore[typing-only-first-party-import]
from src.profiles.affixes import (  # ruff:ignore[typing-only-first-party-import]
    AffixFilterCountModel,
    AspectUniqueFilterModel,
)
from src.profiles.validation.constraints import check_greater_than_zero, validate_greater_affix_count
from src.profiles.validation.normalization import (
    _normalize_rarities,
    _parse_item_type_or_rarities,
    _validate_affix_pool_names,
    _validate_set_name,
)


class ItemFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
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
    def parse_unique_aspect(cls, data: dict[str, object] | list[dict[str, object]] | None) -> list[dict[str, object]]:
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
        from src.item import Dataloader  # ruff:ignore[import-outside-top-level]

        affix_dict = Dataloader().affix_dict
        _validate_affix_pool_names(self.affix_pool, affix_dict, "affixPool")
        _validate_affix_pool_names(self.inherent_pool, affix_dict, "inherentPool")
        return self


DynamicItemFilterModel = RootModel[dict[str, ItemFilterModel]]


class _BaseSealOrCharmFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
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
        normalized_sets: list[str] = []
        for name in sets:
            normalized_name = _validate_set_name(name, "set")
            if normalized_name is None:
                msg = "set name must not be empty"
                raise ValueError(msg)
            normalized_sets.append(normalized_name)
        return normalized_sets

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
        from src.item import Dataloader  # ruff:ignore[import-outside-top-level]

        _validate_affix_pool_names(self.affix_pool, Dataloader().charm_affix_dict, "affixPool")
        return self


class SealFilterModel(_BaseSealOrCharmFilterModel):
    @model_validator(mode="after")
    def affix_names_must_match_seal_pool(self) -> SealFilterModel:
        # This on module level would be a circular import, so we do it lazy for now
        from src.item import Dataloader  # ruff:ignore[import-outside-top-level]

        _validate_affix_pool_names(self.affix_pool, Dataloader().seal_affix_dict, "affixPool")
        return self


DynamicCharmFilterModel = RootModel[dict[str, CharmFilterModel]]
DynamicSealFilterModel = RootModel[dict[str, SealFilterModel]]
