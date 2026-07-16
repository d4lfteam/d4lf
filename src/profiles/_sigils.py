import enum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from src.item import ItemRarity  # ruff:ignore[typing-only-first-party-import]
from src.profiles._validation import _normalize_rarities, _normalize_tribute_names


class SigilPriority(enum.StrEnum):
    blacklist = enum.auto()
    whitelist = enum.auto()


class SigilConditionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    condition: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def parse_data(cls, data: str | list[str] | dict[str, object]) -> dict[str, object]:
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
        from src.item import SigilRules  # ruff:ignore[import-outside-top-level]

        names = [names_in] if isinstance(names_in, str) else names_in
        sigil_rules = SigilRules.default()
        errors = [name for name in names if not sigil_rules.target(name).known]
        if errors:
            msg = f"The following affixes/dungeons do not exist: {errors}"
            raise ValueError(msg)
        return names_in


class SigilFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
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
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
    name: list[str] = []
    rarities: list[ItemRarity] = Field(
        default=[], validation_alias=AliasChoices("rarity", "rarities"), serialization_alias="rarity"
    )

    @field_validator("name", mode="before")
    @classmethod
    def parse_names(cls, data: str | list[str] | None) -> list[str]:
        return _normalize_tribute_names(data)

    @field_validator("rarities", mode="before")
    @classmethod
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _normalize_rarities(data)
