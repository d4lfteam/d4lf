from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.profiles._affixes import GlobalUniqueModel  # ruff:ignore[typing-only-first-party-import]
from src.profiles._equipment import (  # ruff:ignore[typing-only-first-party-import]
    DynamicCharmFilterModel,
    DynamicItemFilterModel,
    DynamicSealFilterModel,
)
from src.profiles._paragon import ParagonPayloadModel  # ruff:ignore[typing-only-first-party-import]
from src.profiles._sigils import SigilFilterModel, SigilPriority, TributeFilterModel
from src.profiles._validation import _as_string_keyed_dict, _legacy_filter_values


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_by_name=True, validate_by_alias=True)
    affixes: list[DynamicItemFilterModel] = Field(default=[], alias="Affixes")
    aspect_upgrades: list[str] = Field(default=[], alias="AspectUpgrades")
    charms: list[DynamicCharmFilterModel] = Field(default=[], alias="Charms")
    global_uniques: list[GlobalUniqueModel] = Field(default=[], alias="GlobalUniques")
    name: str
    seals: list[DynamicSealFilterModel] = Field(default=[], alias="Seals")
    sigils: SigilFilterModel = Field(
        default=SigilFilterModel(blacklist=[], whitelist=[], priority=SigilPriority.blacklist), alias="Sigils"
    )
    tributes: TributeFilterModel | None = Field(default=None, alias="Tributes")
    paragon: ParagonPayloadModel | None = Field(default=None, alias="Paragon")

    @model_validator(mode="before")
    @classmethod
    def migrate_list_tributes(cls, data: object) -> object:
        """Merge legacy list-shaped Tributes into a single object."""
        data_dict = _as_string_keyed_dict(data)
        if data_dict is None:
            return data
        key = "Tributes" if "Tributes" in data_dict else "tributes" if "tributes" in data_dict else None
        if key is None:
            return data
        tributes = data_dict[key]
        if not isinstance(tributes, list):
            return data
        names: list[object] = []
        rarities: list[object] = []
        for entry in tributes:
            entry_dict = _as_string_keyed_dict(entry)
            if entry_dict is None:
                msg = "Legacy Tributes entries must be mappings"
                raise ValueError(msg)
            unknown_keys = [key for key in entry_dict if key not in {"name", "rarity", "rarities"}]
            if unknown_keys:
                msg = f"Legacy Tributes entries contain unsupported keys: {unknown_keys}"
                raise ValueError(msg)
            if "rarity" in entry_dict and "rarities" in entry_dict:
                msg = "Legacy Tributes entries must not contain both rarity and rarities"
                raise ValueError(msg)

            raw_names = entry_dict.get("name")
            names_in_entry = _legacy_filter_values(raw_names) if "name" in entry_dict else []
            for name in names_in_entry:
                if name not in names:
                    names.append(name)

            raw_rarities = entry_dict.get("rarity", entry_dict.get("rarities"))
            rarities_in_entry = (
                _legacy_filter_values(raw_rarities) if "rarity" in entry_dict or "rarities" in entry_dict else []
            )
            for rarity in rarities_in_entry:
                if rarity not in rarities:
                    rarities.append(rarity)
        return {**data_dict, key: {"name": names, "rarity": rarities} if names or rarities else {}}

    @model_validator(mode="before")
    @classmethod
    def aspects_must_exist(cls, data: object) -> object:
        # This on module level would be a circular import, so we do it lazy for now
        from src.item import Dataloader  # ruff:ignore[import-outside-top-level]

        data_dict = _as_string_keyed_dict(data)
        if data_dict is None:
            return data

        # Check both snake_case and camelCase (alias) keys
        aspect_key = "aspect_upgrades" if "aspect_upgrades" in data_dict else "AspectUpgrades"
        if aspect_key not in data_dict:
            return data

        all_aspects_list = Dataloader().aspect_list
        raw_aspects = data_dict[aspect_key]
        if not isinstance(raw_aspects, list):
            return data
        aspect_names: list[str] = []
        for aspect in raw_aspects:
            if not isinstance(aspect, str):
                return data
            aspect_names.append(aspect)
        aspects_not_in_all_aspects = [x for x in aspect_names if x not in all_aspects_list]
        if aspects_not_in_all_aspects:
            msg = f"The following aspects in AspectUpgrades do not exist in our data: {', '.join(aspects_not_in_all_aspects)}"
            raise ValueError(msg)

        return data

    @model_validator(mode="before")
    @classmethod
    def normalize_paragon(cls, data: object) -> object:
        data_dict = _as_string_keyed_dict(data)
        if data_dict is None:
            return data

        key = "Paragon" if "Paragon" in data_dict else "paragon" if "paragon" in data_dict else None
        if key is None:
            return data

        paragon = data_dict[key]
        if paragon is None:
            return data
        if not isinstance(paragon, list):
            return data
        if not paragon:
            return {**data_dict, key: None}
        if len(paragon) > 1:
            msg = "Paragon must contain at most one payload"
            raise ValueError(msg)
        paragon_payload = _as_string_keyed_dict(paragon[0])
        if paragon_payload is None:
            msg = "Paragon legacy list entries must be objects"
            raise ValueError(msg)
        return {**data_dict, key: paragon_payload}

    @field_serializer("paragon", when_used="json-unless-none")
    def serialize_paragon(self, paragon: ParagonPayloadModel | None) -> object:
        if paragon is None:
            return None
        return paragon.model_dump(mode="python", by_alias=True, exclude_none=True, exclude_defaults=True)
