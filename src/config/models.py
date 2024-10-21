"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import enum
import logging
import sys

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator
from pydantic_numpy import np_array_pydantic_annotated_typing
from pydantic_numpy.model import NumpyModel

from src.config.helper import check_greater_than_zero, validate_hotkey
from src.item.data.item_type import ItemType

MODULE_LOGGER = logging.getLogger(__name__)
HIDE_FROM_GUI_KEY = "hide_from_gui"
IS_HOTKEY_KEY = "is_hotkey"

DEPRECATED_INI_KEYS = [
    "hidden_transparency",
    "import_build",
    "local_prefs_path",
    "move_item_type",
]


class AspectFilterType(enum.StrEnum):
    all = enum.auto()
    none = enum.auto()
    upgrade = enum.auto()


class ComparisonType(enum.StrEnum):
    larger = enum.auto()
    smaller = enum.auto()


class HandleRaresType(enum.StrEnum):
    filter = enum.auto()
    ignore = enum.auto()
    junk = enum.auto()


class ItemRefreshType(enum.StrEnum):
    force_with_filter = enum.auto()
    force_without_filter = enum.auto()
    no_refresh = enum.auto()


class LogLevels(enum.StrEnum):
    debug = enum.auto()
    info = enum.auto()
    warning = enum.auto()
    error = enum.auto()
    critical = enum.auto()


class MoveItemsType(enum.StrEnum):
    everything = enum.auto()
    favorites = enum.auto()
    junk = enum.auto()
    unmarked = enum.auto()


class UnfilteredUniquesType(enum.StrEnum):
    favorite = enum.auto()
    ignore = enum.auto()
    junk = enum.auto()


class UseTTSType(enum.StrEnum):
    full = enum.auto()
    mixed = enum.auto()
    off = enum.auto()


class _IniBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


def _parse_item_type(data: str | list[str]) -> list[str]:
    if isinstance(data, str):
        return [data]
    return data


class AffixAspectFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    value: float | None = None
    comparison: ComparisonType = ComparisonType.larger

    @model_validator(mode="before")
    def parse_data(cls, data: str | list[str] | list[str | float] | dict[str, str | float]) -> dict[str, str | float]:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return {"name": data}
        if isinstance(data, list):
            if not data or len(data) > 3:
                raise ValueError("list, cannot be empty or larger than 3 items")
            result = {}
            if len(data) >= 1:
                result["name"] = data[0]
            if len(data) >= 2:
                result["value"] = data[1]
            if len(data) == 3:
                result["comparison"] = data[2]
            return result
        raise ValueError("must be str or list")


class AffixFilterModel(AffixAspectFilterModel):
    @field_validator("name")
    def name_must_exist(cls, name: str) -> str:
        from src.dataloader import Dataloader  # This on module level would be a circular import, so we do it lazy for now

        if name not in Dataloader().affix_dict:
            raise ValueError(f"affix {name} does not exist")
        return name


class AffixFilterCountModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: list[AffixFilterModel] = []
    maxCount: int = sys.maxsize
    minCount: int = 0
    minGreaterAffixCount: int = 0

    @field_validator("minCount", "minGreaterAffixCount", "maxCount")
    def count_validator(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @model_validator(mode="after")
    def model_validator(self) -> "AffixFilterCountModel":
        # If minCount and maxCount are not set, we assume that the lengths of the count list is the only thing that matters.
        # To not show up in the model.dict() we need to remove them from the model_fields_set property
        if "minCount" not in self.model_fields_set and "maxCount" not in self.model_fields_set:
            self.minCount = len(self.count)
            self.maxCount = len(self.count)
            self.model_fields_set.remove("minCount")
            self.model_fields_set.remove("maxCount")
        if self.minCount > self.maxCount:
            raise ValueError("minCount must be smaller than maxCount")
        if not self.count:
            raise ValueError("count must not be empty")
        return self


class AspectUniqueFilterModel(AffixAspectFilterModel):
    @field_validator("name")
    def name_must_exist(cls, name: str) -> str:
        from src.dataloader import Dataloader  # This on module level would be a circular import, so we do it lazy for now

        # Ensure name is in format we expect
        name = name.lower().replace("'", "").replace(" ", "_").replace(",", "")

        if name not in Dataloader().aspect_unique_dict:
            raise ValueError(f"affix {name} does not exist")
        return name


class AdvancedOptionsModel(_IniBaseModel):
    exit_key: str = Field(default="f12", description="Hotkey to exit d4lf", json_schema_extra={IS_HOTKEY_KEY: "True"})
    force_refresh_only: str = Field(
        default="ctrl+shift+f11",
        description="Hotkey to refresh the junk/favorite status of all items in your inventory/stash. A filter is not run after.",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    log_lvl: LogLevels = Field(default=LogLevels.info, description="The level at which logs are written")
    move_to_chest: str = Field(
        default="f8", description="Hotkey to move configured items from inventory to stash", json_schema_extra={IS_HOTKEY_KEY: "True"}
    )
    move_to_inv: str = Field(
        default="f7", description="Hotkey to move configured items from stash to inventory", json_schema_extra={IS_HOTKEY_KEY: "True"}
    )
    process_name: str = Field(
        default="Diablo IV.exe",
        description="The process that is running Diablo 4. Could help usage when playing through a streaming service like GeForce Now",
    )
    run_filter: str = Field(default="f11", description="Hotkey to run the filter process", json_schema_extra={IS_HOTKEY_KEY: "True"})
    run_filter_force_refresh: str = Field(
        default="shift+f11",
        description="Hotkey to run the filter process with a force refresh. The status of all junk/favorite items will be reset",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    run_scripts: str = Field(
        default="f9", description="Hotkey to enable/disable the vision filter", json_schema_extra={IS_HOTKEY_KEY: "True"}
    )
    scripts: list[str] = Field(default=["vision_mode"], json_schema_extra={HIDE_FROM_GUI_KEY: "True"})
    vision_mode_only: bool = Field(
        default=False, description="Only allow vision mode to run. All hotkeys and actions that click will be disabled."
    )

    @model_validator(mode="after")
    def key_must_be_unique(self) -> "AdvancedOptionsModel":
        keys = [
            self.exit_key,
            self.force_refresh_only,
            self.move_to_chest,
            self.move_to_inv,
            self.run_filter,
            self.run_filter_force_refresh,
            self.run_scripts,
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("hotkeys must be unique")
        return self

    @field_validator(
        "exit_key", "force_refresh_only", "move_to_chest", "move_to_inv", "run_filter", "run_filter_force_refresh", "run_scripts"
    )
    def key_must_exist(cls, k: str) -> str:
        return validate_hotkey(k)

    @field_validator("scripts", mode="before")
    def check_scripts_is_list(cls, v: str) -> list[str]:
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            raise ValueError("must be a list or a string")
        return v


class CharModel(_IniBaseModel):
    inventory: str = Field(default="i", description="Hotkey in Diablo IV to open inventory", json_schema_extra={IS_HOTKEY_KEY: "True"})

    @field_validator("inventory")
    def key_must_exist(cls, k: str) -> str:
        return validate_hotkey(k)


class ColorsModel(_IniBaseModel):
    material_color: "HSVRangeModel"
    unique_gold: "HSVRangeModel"
    unusable_red: "HSVRangeModel"


class BrowserType(enum.StrEnum):
    edge = enum.auto()
    chrome = enum.auto()
    firefox = enum.auto()


class GeneralModel(_IniBaseModel):
    browser: BrowserType = Field(default=BrowserType.chrome, description="Which browser to use to get builds")
    check_chest_tabs: list[int] = Field(default=[0, 1], description="Which tabs to check. Note: All 6 Tabs must be unlocked!")
    full_dump: bool = Field(
        default=False,
        description="When using the import build feature, whether to use the full dump (e.g. contains all filter items) or not",
    )
    handle_rares: HandleRaresType = Field(default=HandleRaresType.filter, description="How to handle rares that the filter finds.")
    handle_uniques: UnfilteredUniquesType = Field(
        default=UnfilteredUniquesType.favorite,
        description="What should be done with uniques that do not match any profile. Mythics are always favorited. If mark_as_favorite is unchecked then uniques that match a profile will not be favorited.",
    )
    keep_aspects: AspectFilterType = Field(
        default=AspectFilterType.upgrade, description="Whether to keep aspects that didn't match a filter"
    )
    language: str = Field(
        default="enUS", description="Do not change. Only English is supported at this time", json_schema_extra={HIDE_FROM_GUI_KEY: "True"}
    )
    mark_as_favorite: bool = Field(
        default=True,
        description="Whether to favorite matched items or not",
    )
    minimum_overlay_font_size: int = Field(
        default=12,
        description="The minimum font size for the vision overlay, specifically the green text that shows which filter(s) are matching.",
    )
    move_to_inv_item_type: list[MoveItemsType] = Field(
        default=[MoveItemsType.everything],
        description="When doing stash/inventory transfer, what types of items should be moved",
    )
    move_to_stash_item_type: list[MoveItemsType] = Field(
        default=[MoveItemsType.everything],
        description="When doing stash/inventory transfer, what types of items should be moved",
    )
    profiles: list[str] = Field(
        default=[],
        description='Which filter profiles should be run. All .yaml files with "Aspects" and '
        '"Affixes" sections will be used from '
        "C:/Users/USERNAME/.d4lf/profiles/*.yaml",
    )
    run_vision_mode_on_startup: bool = Field(default=True, description="Whether to run vision mode on startup or not")
    use_tts: UseTTSType = Field(default=UseTTSType.off, description="Whether to use tts or not")

    @field_validator("check_chest_tabs", mode="before")
    def check_chest_tabs_index(cls, v: str) -> list[int]:
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            raise ValueError("must be a list or a string")
        return sorted([int(x) - 1 for x in v])

    @field_validator("profiles", mode="before")
    def check_profiles_is_list(cls, v: str) -> list[str]:
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            raise ValueError("must be a list or a string")
        return [v.strip() for v in v]

    @field_validator("language")
    def language_must_exist(cls, v: str) -> str:
        if v not in ["enUS"]:
            raise ValueError("language not supported")
        return v

    @field_validator("minimum_overlay_font_size")
    def font_size_in_range(cls, v: int) -> int:
        if not 10 <= v <= 20:
            raise ValueError("Font size must be between 10 and 20, inclusive")
        return v

    @field_validator("move_to_inv_item_type", "move_to_stash_item_type", mode="before")
    def convert_move_item_type(cls, v: str):
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            raise ValueError("must be a list or a string")
        return [MoveItemsType[v.strip()] for v in v]

    @model_validator(mode="before")
    def check_deprecation(cls, data) -> dict:
        # removed non_favorites from MoveItemsType
        for key in ["move_to_inv_item_type", "move_to_stash_item_type"]:
            if key in data and data[key] == "non_favorites":
                data[key] = [MoveItemsType.junk, MoveItemsType.unmarked]
                MODULE_LOGGER.warning(
                    f"{key}=non_favorites is deprecated. Changing to equivalent of junk and unmarked instead. Modify this value in the GUI to remove this message."
                )
        return data


class HSVRangeModel(_IniBaseModel):
    h_s_v_min: np_array_pydantic_annotated_typing(dimensions=1)
    h_s_v_max: np_array_pydantic_annotated_typing(dimensions=1)

    def __getitem__(self, index):
        # TODO added this to not have to change much of the other code. should be fixed some time
        if index == 0:
            return self.h_s_v_min
        if index == 1:
            return self.h_s_v_max
        raise IndexError("Index out of range")

    @model_validator(mode="after")
    def check_interval_sanity(self) -> "HSVRangeModel":
        if self.h_s_v_min[0] > self.h_s_v_max[0]:
            raise ValueError(f"invalid hue range [{self.h_s_v_min[0]}, {self.h_s_v_max[0]}]")
        if self.h_s_v_min[1] > self.h_s_v_max[1]:
            raise ValueError(f"invalid saturation range [{self.h_s_v_min[1]}, {self.h_s_v_max[1]}]")
        if self.h_s_v_min[2] > self.h_s_v_max[2]:
            raise ValueError(f"invalid value range [{self.h_s_v_min[2]}, {self.h_s_v_max[2]}]")
        return self

    @field_validator("h_s_v_min", "h_s_v_max")
    def values_in_range(cls, v: np.ndarray) -> np.ndarray:
        if not len(v) == 3:
            raise ValueError("must be h,s,v")
        if not -179 <= v[0] <= 179:
            raise ValueError("must be in [-179, 179]")
        if not all(0 <= x <= 255 for x in v[1:3]):
            raise ValueError("must be in [0, 255]")
        return v


class ItemFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    affixPool: list[AffixFilterCountModel] = []
    inherentPool: list[AffixFilterCountModel] = []
    itemType: list[ItemType] = []
    minGreaterAffixCount: int = 0
    minPower: int = 0

    @field_validator("minPower")
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("minGreaterAffixCount")
    def min_greater_affix_in_range(cls, v: int) -> int:
        if not 0 <= v <= 3:
            raise ValueError("must be in [0, 3]")
        return v

    @field_validator("itemType", mode="before")
    def parse_item_type(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type(data)


DynamicItemFilterModel = RootModel[dict[str, ItemFilterModel]]


class SigilPriority(enum.StrEnum):
    blacklist = enum.auto()
    whitelist = enum.auto()


class SigilConditionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    condition: list[str] = []

    @model_validator(mode="before")
    def parse_data(cls, data: str | list[str] | list[str | float] | dict[str, str | float]) -> dict[str, str | float]:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return {"name": data}
        if isinstance(data, list):
            if not data:
                raise ValueError("list cannot be empty")
            result = {}
            if len(data) >= 1:
                result["name"] = data[0]
            if len(data) >= 2:
                result["condition"] = data[1:]
            return result
        raise ValueError("must be str or list")

    @field_validator("condition", "name")
    def name_must_exist(cls, names_in: str | list[str]) -> str | list[str]:
        from src.dataloader import Dataloader  # This on module level would be a circular import, so we do it lazy for now

        names = [names_in] if isinstance(names_in, str) else names_in
        errors = [name for name in names if name not in Dataloader().affix_sigil_dict]
        if errors:
            raise ValueError(f"The following affixes/dungeons do not exist: {errors}")
        return names_in


class SigilFilterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blacklist: list[SigilConditionModel] = []
    maxTier: int = sys.maxsize
    minTier: int = 0
    priority: SigilPriority = SigilPriority.blacklist
    whitelist: list[SigilConditionModel] = []

    @model_validator(mode="after")
    def data_integrity(self) -> "SigilFilterModel":
        errors = [item for item in self.blacklist if item in self.whitelist]
        if errors:
            raise ValueError(f"blacklist and whitelist must not overlap: {errors}")
        if self.minTier > self.maxTier:
            raise ValueError("minTier must be smaller than maxTier")
        return self

    @field_validator("minTier", "maxTier")
    def min_max_tier_in_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("must be in [0, 100]")
        return v


class UniqueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: AspectUniqueFilterModel = None  # Aspect needs to stay on top so the model is written how people expect
    affix: list[AffixFilterModel] = []
    itemType: list[ItemType] = []
    profileAlias: str = ""
    minGreaterAffixCount: int = 0
    minPower: int = 0
    mythic: bool = False

    @field_validator("minPower")
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("minGreaterAffixCount")
    def count_validator(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("itemType", mode="before")
    def parse_item_type(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type(data)


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    Affixes: list[DynamicItemFilterModel] = []
    Sigils: SigilFilterModel | None = None
    Uniques: list[UniqueModel] = []


class UiOffsetsModel(_IniBaseModel):
    find_bullet_points_width: int
    find_seperator_short_offset_top: int
    item_descr_line_height: int
    item_descr_off_bottom_edge: int
    item_descr_pad: int
    item_descr_width: int
    vendor_center_item_x: int


class UiPosModel(_IniBaseModel):
    possible_centers: list[tuple[int, int]]
    window_dimensions: tuple[int, int]


class UiRoiModel(NumpyModel):
    rel_descr_search_left: np_array_pydantic_annotated_typing(dimensions=1)
    rel_descr_search_right: np_array_pydantic_annotated_typing(dimensions=1)
    rel_fav_flag: np_array_pydantic_annotated_typing(dimensions=1)
    slots_3x11: np_array_pydantic_annotated_typing(dimensions=1)
    slots_5x10: np_array_pydantic_annotated_typing(dimensions=1)
    sort_icon: np_array_pydantic_annotated_typing(dimensions=1)
    stash_menu_icon: np_array_pydantic_annotated_typing(dimensions=1)
    tab_slots_6: np_array_pydantic_annotated_typing(dimensions=1)
    vendor_text: np_array_pydantic_annotated_typing(dimensions=1)
