from pydantic import Field, field_validator, model_validator

from src.settings.models.core import (
    CATEGORY_KEY,
    HIDE_FROM_GUI_KEY,
    LIVE_RELOAD_GROUP_KEY,
    MODULE_LOGGER,
    AspectFilterType,
    BrowserType,
    CosmeticFilterType,
    MoveItemsType,
    SettingsCategory,
    ThemeType,
    UnfilteredUniquesType,
    VisionModeType,
    _IniBaseModel,
)


class GeneralModel(_IniBaseModel):
    @model_validator(mode="before")
    @classmethod
    def check_move_items_deprecation(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        migrated_data = dict(data)
        for key in ["move_to_inv_item_type", "move_to_stash_item_type"]:
            val = migrated_data.get(key)
            if val is None:
                continue
            items = []
            if isinstance(val, str):
                items = [i.strip().lower() for i in val.split(",") if i.strip()]
            elif isinstance(val, list):
                items = [str(i).lower() for i in val]
            if "everything" in items:
                MODULE_LOGGER.warning("Deprecated 'everything' value found in %s. Converting it to explicit list.", key)
                migrated_data[key] = [MoveItemsType.favorites, MoveItemsType.junk, MoveItemsType.unmarked]
        return migrated_data

    auto_use_temper_manuals: bool = Field(
        default=True,
        description="When using the loot filter, should found temper manuals be automatically used? Note: Will not work with stash open.",
        title="Auto-use Temper Manuals",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.AUTOMATION},
    )
    browser: BrowserType = Field(
        default=BrowserType.chrome,
        description="Which browser to use to get builds",
        title="Browser",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.SYSTEM},
    )
    check_chest_tabs: list[int] = Field(
        default=[0, 1],
        description="Which stash tabs to check. Note: All tabs available (6 or 7) must be unlocked!",
        title="Stash Tabs to Filter",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.STASH},
    )
    do_not_junk_ancestral_legendaries: bool = Field(
        default=False,
        description="Do not mark ancestral legendaries as junk",
        title="Protective Ancestral Filter",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.LOOT},
    )
    full_dump: bool = Field(
        default=False,
        description="When using the import build feature, whether to use the full dump (e.g. contains all filter items) or not",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.ADVANCED},
    )
    handle_cosmetics: CosmeticFilterType = Field(
        default=CosmeticFilterType.ignore,
        description="What should be done with cosmetic upgrades that do not match any filter",
        title="Handle Cosmetics",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.LOOT},
    )
    handle_uniques: UnfilteredUniquesType = Field(
        default=UnfilteredUniquesType.favorite,
        description="What should be done with uniques that do not match any profile. Mythics are always favorited. If mark_as_favorite is unchecked then uniques that match a profile will not be favorited.",
        title="Unfiltered Unique Behavior",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.LOOT},
    )
    ignore_escalation_sigils: bool = Field(
        default=True,
        description="When filtering Sigils, should escalation sigils be ignored?",
        title="Ignore Escalation Sigils",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.LOOT},
    )
    keep_aspects: AspectFilterType = Field(
        default=AspectFilterType.upgrade,
        description="Whether to keep aspects that didn't match a filter",
        title="Aspect Upgrade Handling",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.LOOT},
    )
    language: str = Field(
        default="enUS",
        description="Do not change. Only English is supported at this time",
        title="Language",
        json_schema_extra={
            HIDE_FROM_GUI_KEY: "True",
            LIVE_RELOAD_GROUP_KEY: "language",
            CATEGORY_KEY: SettingsCategory.SYSTEM,
        },
    )
    mark_as_favorite: bool = Field(
        default=True,
        description="Whether to favorite matched items or not",
        title="Mark Matched Items as Favorite",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.LOOT},
    )
    max_stash_tabs: int = Field(
        default=7,
        description="The maximum number of stash tabs available.",
        title="Max Stash Tabs",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.STASH},
    )
    minimum_overlay_font_size: int = Field(
        default=12,
        description="The minimum font size for the vision overlays.",
        title="Overlay Text Size",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.UI},
    )
    move_to_inv_item_type: list[MoveItemsType] = Field(
        default=[MoveItemsType.favorites, MoveItemsType.junk, MoveItemsType.unmarked],
        description="When doing stash/inventory transfer, what types of items should be moved",
        title="Move to Inventory Types",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.STASH},
    )
    move_to_stash_item_type: list[MoveItemsType] = Field(
        default=[MoveItemsType.favorites, MoveItemsType.junk, MoveItemsType.unmarked],
        description="When doing stash/inventory transfer, what types of items should be moved",
        title="Move to Stash Types",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.STASH},
    )
    profiles: list[str] = Field(
        default=[],
        description="Which filter profiles should be run.",
        title="Active Filtering Profiles",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.PROFILES},
    )
    run_vision_mode_on_startup: bool = Field(
        default=True,
        description="Whether to run vision mode on startup or not",
        title="Auto-Start Vision Mode",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.AUTOMATION},
    )
    theme: ThemeType = Field(
        default=ThemeType.dark,
        description="GUI Theme",
        title="Theme",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.UI},
    )
    colorblind_mode: bool = Field(
        default=False,
        description="Enable colorblind palette",
        title="Colorblind Accessible Palette",
        json_schema_extra={CATEGORY_KEY: SettingsCategory.UI},
    )
    vision_mode_type: VisionModeType = Field(
        default=VisionModeType.highlight_matches,
        description="Should the vision mode use the slightly slower version that highlights matching affixes, or the immediate version that just shows text of the matches? Note: highlight_matches does not work with controllers.",
        title="Vision Mode Type",
        json_schema_extra={LIVE_RELOAD_GROUP_KEY: "restart_app", CATEGORY_KEY: SettingsCategory.UI},
    )

    @field_validator("check_chest_tabs", mode="before")
    @classmethod
    def check_chest_tabs_index(cls, v: object) -> list[int]:
        if isinstance(v, str):
            return sorted([int(x.strip()) - 1 for x in v.split(",") if x.strip()])
        if isinstance(v, list):
            # Subtract 1 only if the element is a string (external 1-based format)
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(int(item) - 1)
                elif isinstance(item, int) and not isinstance(item, bool):
                    result.append(item)
                else:
                    msg = "list entries must be strings or integers"
                    raise ValueError(msg)
            return sorted(result)
        msg = "must be a list or a string"
        raise ValueError(msg)

    @model_validator(mode="after")
    def validate_stash_tabs(self) -> GeneralModel:
        # Constrain check_chest_tabs to the range [0, max_stash_tabs - 1]
        new_tabs = sorted({t for t in self.check_chest_tabs if 0 <= t < self.max_stash_tabs})
        if new_tabs != self.check_chest_tabs:
            self.__dict__["check_chest_tabs"] = new_tabs
        return self

    @field_validator("max_stash_tabs")
    @classmethod
    def check_max_stash_tabs(cls, v: int) -> int:
        if not 6 <= v <= 7:
            msg = "must be 6 or 7"
            raise ValueError(msg)
        return v

    @field_validator("profiles", mode="before")
    @classmethod
    def check_profiles_is_list(cls, v: object) -> list[str]:
        if isinstance(v, str):
            values = v.split(",")
        elif isinstance(v, list):
            values = v
        else:
            msg = "must be a list or a string"
            raise ValueError(msg)
        if not all(isinstance(item, str) for item in values):
            msg = "profiles must contain only strings"
            raise ValueError(msg)
        profile_names = [item.strip() for item in values if isinstance(item, str)]
        return [profile_name for profile_name in profile_names if profile_name]

    @field_validator("language")
    @classmethod
    def language_must_exist(cls, v: str) -> str:
        if v != "enUS":
            msg = "language not supported"
            raise ValueError(msg)
        return v

    @field_validator("minimum_overlay_font_size")
    @classmethod
    def font_size_in_range(cls, v: int) -> int:
        if not 10 <= v <= 20:
            msg = "Font size must be between 10 and 20, inclusive"
            raise ValueError(msg)
        return v

    @field_validator("move_to_inv_item_type", "move_to_stash_item_type", mode="before")
    @classmethod
    def convert_move_item_type(cls, v: object) -> list[MoveItemsType]:
        if isinstance(v, str):
            values = v.split(",")
        elif isinstance(v, list):
            values = v
        else:
            msg = "must be a list or a string"
            raise ValueError(msg)
        out = []
        for x in values:
            if isinstance(x, MoveItemsType):
                out.append(x)
            elif isinstance(x, str) and (s := x.strip()):
                if s.lower() == "everything":
                    out.extend([MoveItemsType.favorites, MoveItemsType.junk, MoveItemsType.unmarked])
                else:
                    try:
                        out.append(MoveItemsType(s.lower()))
                    except ValueError:
                        MODULE_LOGGER.error("Invalid move item type: %s", s)
        return list(dict.fromkeys(out))
