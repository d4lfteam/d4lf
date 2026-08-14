from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np  # ruff:ignore[typing-only-third-party-import] - runtime type-hint introspection resolves np.ndarray

from src.type_aliases import JsonObject

if TYPE_CHECKING:
    from src.settings.models.core import (
        AspectFilterType,
        BrowserType,
        CosmeticFilterType,
        LogLevels,
        MoveItemsType,
        ThemeType,
        UnfilteredUniquesType,
        VisionModeType,
    )


type SettingValue = (
    bool
    | int
    | float
    | str
    | list[int]
    | list[str]
    | list[MoveItemsType]
    | tuple[int, int]
    | AspectFilterType
    | BrowserType
    | CosmeticFilterType
    | LogLevels
    | ThemeType
    | UnfilteredUniquesType
    | VisionModeType
    | None
)
type SettingInput = SettingValue | JsonObject


@dataclass
class Template:
    name: str = ""
    img_bgra: np.ndarray | None = None
    img_bgr: np.ndarray | None = None
    img_gray: np.ndarray | None = None
    alpha_mask: np.ndarray | None = None
