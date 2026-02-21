"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import enum
import logging
import sys
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator
from pydantic_numpy import np_array_pydantic_annotated_typing  # noqa: TC002
from pydantic_numpy.model import NumpyModel

from src.config.helper import check_greater_than_zero, validate_hotkey
from src.item.data.item_type import ItemType  # noqa: TC001
from src.item.data.rarity import ItemRarity

if TYPE_CHECKING:
    import numpy as np

MODULE_LOGGER = logging.getLogger(__name__)
HIDE_FROM_GUI_KEY = "hide_from_gui"
IS_HOTKEY_KEY = "is_hotkey"

DEPRECATED_INI_KEYS = [
    "hidden_transparency",
    "import_build",
    "local_prefs_path",
    "move_item_type",
    "handle_rares",
    "s7_do_not_junk_ancestral_legendaries",
    "scripts",
]


class AspectFilterType(enum.StrEnum):
    all = enum.auto()
    none = enum.auto()
    upgrade = enum.auto()


class ComparisonType(enum.StrEnum):
    larger = enum.auto()
    smaller = enum.auto()


class CosmeticFilterType(enum.StrEnum):
    junk = enum.auto()
    ignore = enum.auto()


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


class VisionModeType(enum.StrEnum):
    highlight_matches = enum.auto()
    fast = enum.auto()


class _IniBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


def _parse_item_type_or_rarities(data: str | list[str]) -> list[str]:
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
                msg = "list, cannot be empty or larger than 3 items"
                raise ValueError(msg)
            result = {}
            if len(data) >= 1:
                result["name"] = data[0]
            if len(data) >= 2:
                result["value"] = data[1]
            if len(data) == 3:
                result["comparison"] = data[2]
            return result
        msg = "must be str or list"
        raise ValueError(msg)


class AffixFilterModel(AffixAspectFilterModel):
    want_greater: bool = False

    @field_validator("name")
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        if name not in Dataloader().affix_dict:
            msg = f"affix {name} does not exist"
            raise ValueError(msg)
        return name


class AffixFilterCountModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: list[AffixFilterModel] = []
    maxCount: int = sys.maxsize
    minCount: int = 0

    @field_validator("minCount", "maxCount")
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
    @field_validator("name")
    def name_must_exist(cls, name: str) -> str:
        # This on module level would be a circular import, so we do it lazy for now
        from src.dataloader import Dataloader  # noqa: PLC0415

        # Ensure name is in format we expect
        name = name.lower().replace("'", "").replace(" ", "_").replace(",", "")

        if name not in Dataloader().aspect_unique_dict:
            msg = f"aspect {name} does not exist"
            raise ValueError(msg)
        return name


class AdvancedOptionsModel(_IniBaseModel):
    disable_tts_warning: bool = Field(
        default=False,
        description="If TTS is working for you but you are still receiving the warning, check this box to disable it.",
    )
    exit_key: str = Field(default="f12", description="Hotkey to exit d4lf", json_schema_extra={IS_HOTKEY_KEY: "True"})
    fast_vision_mode_coordinates: tuple[int, int] | None = Field(
        default=None,
        description="The top left coordinates of the desired location of the fast vision mode overlay in pixels. For example: (300, 500). Set to blank for default behavior.",
    )
    force_refresh_only: str = Field(
        default="ctrl+shift+f11",
        description="Hotkey to refresh the junk/favorite status of all items in your inventory/stash. A filter is not run after.",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    log_lvl: LogLevels = Field(default=LogLevels.info, description="The level at which logs are written")
    move_to_chest: str = Field(
        default="f8",
        description="Hotkey to move configured items from inventory to stash",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    move_to_inv: str = Field(
        default="f7",
        description="Hotkey to move configured items from stash to inventory",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    process_name: str = Field(
        default="Diablo IV.exe",
        description="The process that is running Diablo 4. Could help usage when playing through a streaming service like GeForce Now",
    )
    run_filter: str = Field(
        default="f11",
        description="Hotkey to run the filter process. If the item matches no profiles, it is marked as junk.",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )

    run_filter_drop: str = Field(
        default="ctrl+f11",
        description="Hotkey to run the filter process. If the item matches no profiles, it is dropped.",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    run_filter_force_refresh: str = Field(
        default="shift+f11",
        description="Hotkey to run the filter process with a force refresh. The status of all junk/favorite items will be reset",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    run_vision_mode: str = Field(
        default="f9", description="Hotkey to enable/disable the vision mode", json_schema_extra={IS_HOTKEY_KEY: "True"}
    )
    toggle_paragon_overlay: str = Field(
        default="f10", description="Hotkey to open/close the Paragon overlay", json_schema_extra={IS_HOTKEY_KEY: "True"}
    )
    vision_mode_only: bool = Field(
        default=False, description="Only allow vision mode to run. All hotkeys and actions that click will be disabled."
    )

    @model_validator(mode="after")
    def key_must_be_unique(self) -> AdvancedOptionsModel:
        keys = [
            self.exit_key,
            self.toggle_paragon_overlay,
            self.force_refresh_only,
            self.move_to_chest,
            self.move_to_inv,
            self.run_filter,
            self.run_filter_drop,
            self.run_filter_force_refresh,
            self.run_vision_mode,
        ]
        if len(set(keys)) != len(keys):
            msg = "hotkeys must be unique"
            raise ValueError(msg)
        return self

    @field_validator(
        "exit_key",
        "toggle_paragon_overlay",
        "force_refresh_only",
        "move_to_chest",
        "move_to_inv",
        "run_filter",
        "run_filter_drop",
        "run_filter_force_refresh",
        "run_vision_mode",
    )
    def key_must_exist(cls, k: str) -> str:
        return validate_hotkey(k)

    @field_validator("fast_vision_mode_coordinates", mode="before")
    def convert_fast_vision_mode_coordinates(cls, v: str) -> tuple[int, int] | None:
        if not v:
            return None
        if isinstance(v, str):
            v = v.strip("()")
            parts = [int(part.strip()) for part in v.replace(",", " ").split()]
            if len(parts) != 2:
                msg = "Expected two integers for coordinates."
                raise ValueError(msg)
            for x in parts:
                check_greater_than_zero(x)
            return parts[0], parts[1]
        if isinstance(v, tuple) and len(v) == 2 and all(isinstance(x, int) for x in v):
            for x in v:
                check_greater_than_zero(x)
            return v[0], v[1]
        msg = "vision_mode_coordinates must be a tuple of two integers or blank"
        raise ValueError(msg)


class CharModel(_IniBaseModel):
    inventory: str = Field(
        default="i", description="Hotkey in Diablo IV to open inventory", json_schema_extra={IS_HOTKEY_KEY: "True"}
    )

    @field_validator("inventory")
    def key_must_exist(cls, k: str) -> str:
        return validate_hotkey(k)


class ColorsModel(_IniBaseModel):
    material_color: HSVRangeModel
    unique_gold: HSVRangeModel
    unusable_red: HSVRangeModel


class BrowserType(enum.StrEnum):
    edge = enum.auto()
    chrome = enum.auto()
    firefox = enum.auto()


class ThemeType(enum.StrEnum):
    dark = enum.auto()
    light = enum.auto()


class GeneralModel(_IniBaseModel):
    auto_use_temper_manuals: bool = Field(
        default=True,
        description="When using the loot filter, should found temper manuals be automatically used? Note: Will not work with stash open.",
    )
    browser: BrowserType = Field(default=BrowserType.chrome, description="Which browser to use to get builds")
    check_chest_tabs: list[int] = Field(
        default=[0, 1], description="Which stash tabs to check. Note: All tabs available (6 or 7) must be unlocked!"
    )
    do_not_junk_ancestral_legendaries: bool = Field(
        default=False, description="Do not mark ancestral legendaries as junk for seasonal challenge"
    )
    full_dump: bool = Field(
        default=False,
        description="When using the import build feature, whether to use the full dump (e.g. contains all filter items) or not",
    )
    handle_cosmetics: CosmeticFilterType = Field(
        default=CosmeticFilterType.ignore,
        description="What should be done with cosmetic upgrades that do not match any filter",
    )
    handle_uniques: UnfilteredUniquesType = Field(
        default=UnfilteredUniquesType.favorite,
        description="What should be done with uniques that do not match any profile. Mythics are always favorited. If mark_as_favorite is unchecked then uniques that match a profile will not be favorited.",
    )
    ignore_escalation_sigils: bool = Field(
        default=True, description="When filtering Sigils, should escalation sigils be ignored?"
    )
    junk_rares: bool = Field(
        default=False, description="Should rares be automatically marked as junk even if they match a filter?"
    )
    keep_aspects: AspectFilterType = Field(
        default=AspectFilterType.upgrade, description="Whether to keep aspects that didn't match a filter"
    )
    language: str = Field(
        default="enUS",
        description="Do not change. Only English is supported at this time",
        json_schema_extra={HIDE_FROM_GUI_KEY: "True"},
    )
    mark_as_favorite: bool = Field(default=True, description="Whether to favorite matched items or not")
    max_stash_tabs: int = Field(
        default=6,
        description="The maximum number of stash tabs you have available to you if you bought them all. If you own the Lord of Hatred expansion you should choose 7. You will need to restart the gui after changing this.",
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
        description='Which filter profiles should be run. All .yaml files with "AspectUpgrades", '
        '"Affixes", "Uniques", "Sigils", etc sections will be used from '
        "C:/Users/USERNAME/.d4lf/profiles/*.yaml",
    )
    run_vision_mode_on_startup: bool = Field(default=True, description="Whether to run vision mode on startup or not")
    theme: ThemeType = Field(default=ThemeType.dark, description="Choose between light and dark theme for the GUI")
    colorblind_mode: bool = Field(
        default=False, description="Enable a colorblind friendly palette for loot filter and paragon overlays"
    )
    vision_mode_type: VisionModeType = Field(
        default=VisionModeType.highlight_matches,
        description="Should the vision mode use the slightly slower version that highlights matching affixes, or the immediate version that just shows text of the matches? Note: highlight_matches does not work with controllers.",
    )

    @field_validator("check_chest_tabs", mode="before")
    def check_chest_tabs_index(cls, v: str) -> list[int]:
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            msg = "must be a list or a string"
            raise ValueError(msg)
        return sorted([int(x) - 1 for x in v])

    @field_validator("max_stash_tabs")
    def check_max_stash_tabs(cls, v: int):
        if not 6 <= v <= 7:
            msg = "must be 6 or 7"
            raise ValueError(msg)
        return v

    @field_validator("profiles", mode="before")
    def check_profiles_is_list(cls, v: str) -> list[str]:
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            msg = "must be a list or a string"
            raise ValueError(msg)
        return [v.strip() for v in v]

    @field_validator("language")
    def language_must_exist(cls, v: str) -> str:
        if v not in ["enUS"]:
            msg = "language not supported"
            raise ValueError(msg)
        return v

    @field_validator("minimum_overlay_font_size")
    def font_size_in_range(cls, v: int) -> int:
        if not 10 <= v <= 20:
            msg = "Font size must be between 10 and 20, inclusive"
            raise ValueError(msg)
        return v

    @field_validator("move_to_inv_item_type", "move_to_stash_item_type", mode="before")
    def convert_move_item_type(cls, v: str):
        if isinstance(v, str):
            v = v.split(",")
        elif not isinstance(v, list):
            msg = "must be a list or a string"
            raise ValueError(msg)
        return [MoveItemsType[v.strip()] for v in v]


class HSVRangeModel(_IniBaseModel):
    h_s_v_min: np_array_pydantic_annotated_typing(dimensions=1)
    h_s_v_max: np_array_pydantic_annotated_typing(dimensions=1)

    def __getitem__(self, index):
        # TODO added this to not have to change much of the other code. should be fixed some time
        if index == 0:
            return self.h_s_v_min
        if index == 1:
            return self.h_s_v_max
        msg = "Index out of range"
        raise IndexError(msg)

    @model_validator(mode="after")
    def check_interval_sanity(self) -> HSVRangeModel:
        if self.h_s_v_min[0] > self.h_s_v_max[0]:
            msg = f"invalid hue range [{self.h_s_v_min[0]}, {self.h_s_v_max[0]}]"
            raise ValueError(msg)
        if self.h_s_v_min[1] > self.h_s_v_max[1]:
            msg = f"invalid saturation range [{self.h_s_v_min[1]}, {self.h_s_v_max[1]}]"
            raise ValueError(msg)
        if self.h_s_v_min[2] > self.h_s_v_max[2]:
            msg = f"invalid value range [{self.h_s_v_min[2]}, {self.h_s_v_max[2]}]"
            raise ValueError(msg)
        return self

    @field_validator("h_s_v_min", "h_s_v_max")
    def values_in_range(cls, v: np.ndarray) -> np.ndarray:
        if len(v) != 3:
            msg = "must be h,s,v"
            raise ValueError(msg)
        if not -179 <= v[0] <= 179:
            msg = "must be in [-179, 179]"
            raise ValueError(msg)
        if not all(0 <= x <= 255 for x in v[1:3]):
            msg = "must be in [0, 255]"
            raise ValueError(msg)
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
        if not 0 <= v <= 4:
            msg = "must be in [0, 4]"
            raise ValueError(msg)
        return v

    @field_validator("itemType", mode="before")
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
    def parse_rarities(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)


class UniqueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aspect: AspectUniqueFilterModel = None  # Aspect needs to stay on top so the model is written how people expect
    affix: list[AffixFilterModel] = []
    itemType: list[ItemType] = []
    profileAlias: str = ""
    minGreaterAffixCount: int = 0
    minPercentOfAspect: int = 0
    minPower: int = 0
    mythic: bool = False

    @field_validator("minPower")
    def check_min_power(cls, v: int) -> int:
        return check_greater_than_zero(v)

    @field_validator("minGreaterAffixCount")
    def count_validator(cls, v: int) -> int:
        if not 0 <= v <= 4:  # Changed to match ItemFilterModel
            msg = "must be in [0, 4]"
            raise ValueError(msg)
        return v

    @field_validator("minPercentOfAspect")
    def percent_validator(cls, v: int) -> int:
        check_greater_than_zero(v)
        if v > 100:
            msg = "must be less than or equal to 100"
            raise ValueError(msg)
        return v

    @field_validator("itemType", mode="before")
    def parse_item_type(cls, data: str | list[str]) -> list[str]:
        return _parse_item_type_or_rarities(data)


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Affixes: list[DynamicItemFilterModel] = []
    AspectUpgrades: list[str] = []
    name: str
    Sigils: SigilFilterModel = SigilFilterModel(blacklist=[], whitelist=[], priority=SigilPriority.blacklist)
    Tributes: list[TributeFilterModel] = []
    Uniques: list[UniqueModel] = []
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
    slots_8x1: np_array_pydantic_annotated_typing(dimensions=1)
    slots_3x11: np_array_pydantic_annotated_typing(dimensions=1)
    slots_5x10: np_array_pydantic_annotated_typing(dimensions=1)
    sort_icon: np_array_pydantic_annotated_typing(dimensions=1)
    stash_menu_icon: np_array_pydantic_annotated_typing(dimensions=1)
    tab_slots: np_array_pydantic_annotated_typing(dimensions=1)
    vendor_menu_icon: np_array_pydantic_annotated_typing(dimensions=1)
