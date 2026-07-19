import enum
import logging
from typing import Annotated

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_numpy.helper.annotation import NpArrayPydanticAnnotation

from src.settings.validation import check_greater_than_zero, validate_hotkey

type Np1DArray = Annotated[
    np.ndarray[tuple[int, ...], np.dtype[np.generic]],
    NpArrayPydanticAnnotation.factory(data_type=None, dimensions=1, strict_data_typing=False),
]

MODULE_LOGGER = logging.getLogger(__name__)
HIDE_FROM_GUI_KEY = "hide_from_gui"
IS_HOTKEY_KEY = "is_hotkey"
CATEGORY_KEY = "category"


class SettingsCategory(enum.StrEnum):
    LOOT = "📦 Loot Behavior"
    PROFILES = "📄 Profiles"
    AUTOMATION = "🤖 Automation"
    STASH = "🎒 Stash & Transfer"
    UI = "🎨 UI & Theme"
    SYSTEM = "⚙️ System & Paths"
    HOTKEYS = "⌨️ Hotkeys"
    ADVANCED = "🛠️ Advanced"


CATEGORY_ORDER = [
    SettingsCategory.PROFILES,
    SettingsCategory.LOOT,
    SettingsCategory.AUTOMATION,
    SettingsCategory.STASH,
    SettingsCategory.UI,
    SettingsCategory.SYSTEM,
    SettingsCategory.HOTKEYS,
    SettingsCategory.ADVANCED,
]


LIVE_RELOAD_GROUP_KEY = "live_reload_group"


class AspectFilterType(enum.StrEnum):
    all = enum.auto()
    none = enum.auto()
    upgrade = enum.auto()


class BrowserType(enum.StrEnum):
    edge = enum.auto()
    chrome = enum.auto()
    firefox = enum.auto()


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
    favorites = enum.auto()
    junk = enum.auto()
    unmarked = enum.auto()


class ThemeType(enum.StrEnum):
    dark = enum.auto()
    light = enum.auto()


class UnfilteredUniquesType(enum.StrEnum):
    favorite = enum.auto()
    ignore = enum.auto()
    junk = enum.auto()


class VisionModeType(enum.StrEnum):
    highlight_matches = enum.auto()
    fast = enum.auto()


class _IniBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class AdvancedOptionsModel(_IniBaseModel):
    disable_tts_warning: bool = Field(
        default=False,
        description="If TTS is working for you but you are still receiving the warning, check this box to disable it.",
        title="Disable TTS Warning",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.ADVANCED},
    )
    exit_key: str = Field(default="f12", description="Hotkey to exit d4lf", json_schema_extra={IS_HOTKEY_KEY: "True"})
    fast_vision_mode_coordinates: tuple[int, int] | None = Field(
        default=None,
        description="The top left coordinates of the desired location of the fast vision mode overlay in pixels. For example: (300, 500). Set to blank for default behavior.",
        title="Fast Vision Mode Coordinates",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.ADVANCED},
    )
    force_refresh_only: str = Field(
        default="ctrl+shift+f11",
        description="Hotkey to refresh the junk/favorite status of all items in your inventory/stash. A filter is not run after.",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    info_overlay: str = Field(
        default="f6",
        description="Hotkey to open/close the info panel overlay",
        json_schema_extra={IS_HOTKEY_KEY: "True"},
    )
    log_lvl: LogLevels = Field(
        default=LogLevels.info,
        description="The level at which logs are written",
        title="Logging Detail Level",
        json_schema_extra={LIVE_RELOAD_GROUP_KEY: "log_level", CATEGORY_KEY: SettingsCategory.ADVANCED},
    )
    log_timestamp: bool = Field(
        default=False,
        description="Include timestamps in Dashboard and Full Logs messages. Log files always include timestamps.",
        title="Show Timestamps In Logs",
        json_schema_extra={LIVE_RELOAD_GROUP_KEY: "log_level", CATEGORY_KEY: SettingsCategory.ADVANCED},
    )
    technical_log_info: bool = Field(
        default=False,
        description=(
            "Include technical information (thread, level, logger name, line number) in Dashboard and Full Logs "
            "messages. Log files always include this information."
        ),
        title="Show Technical Information In Logs",
        json_schema_extra={LIVE_RELOAD_GROUP_KEY: "log_level", CATEGORY_KEY: SettingsCategory.ADVANCED},
    )
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
        description="The process that is running Diablo 4. You should never need to change this.",
        title="Diablo IV Process Name",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.ADVANCED},
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
        default=False,
        description="Only allow vision mode to run. All hotkeys and actions that click will be disabled.",
        title="Vision Mode Only",
        json_schema_extra={LIVE_RELOAD_GROUP_KEY: "hotkeys", CATEGORY_KEY: SettingsCategory.AUTOMATION},
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
            self.info_overlay,
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
        "info_overlay",
    )
    @classmethod
    def key_must_exist(cls, k: str) -> str:
        return validate_hotkey(k)

    @field_validator("fast_vision_mode_coordinates", mode="before")
    @classmethod
    def convert_fast_vision_mode_coordinates(cls, v: str) -> tuple[int, int] | None:
        if not v:
            return None
        if isinstance(v, str):
            if v == "None":
                return None
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
        default="i",
        description="Hotkey in Diablo IV to open inventory",
        title="Inventory Hotkey",
        json_schema_extra={IS_HOTKEY_KEY: "True", CATEGORY_KEY: SettingsCategory.HOTKEYS},
    )

    @field_validator("inventory")
    @classmethod
    def key_must_exist(cls, k: str) -> str:
        return validate_hotkey(k)
