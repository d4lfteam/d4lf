"""Typed contracts and runtime configuration for the Paragon overlay."""

import tkinter as tk
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn, TypedDict

from src.paragon.overlay.theme import PANEL_W

if TYPE_CHECKING:
    from src.profiles import ParagonBoardModel

type TkOption = str | int | float | bool | tk.PhotoImage | tuple[str, int] | tuple[str, int, str]


class OverlayContract(tk.Toplevel):
    """Shared Tk and widget-attribute contract for the overlay mixins."""

    _build_popup_bind_id: str | None
    _build_popup_escape_bind_id: str | None
    _last_roi: tuple[int, int, int, int] | None
    _last_res: tuple[int, int] | None
    grid_x: int
    grid_y: int
    grid_x_collapsed: int
    grid_y_collapsed: int

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(name)


class OverlaySettings(TypedDict, total=False):
    cell_size: int | None
    profile: str | None
    build_name: str | None
    build_idx: int | None
    board_idx: int | None
    grid_x: int | None
    grid_y: int | None
    is_collapsed: bool | None
    cell_size_collapsed: int | None
    grid_x_collapsed: int | None
    grid_y_collapsed: int | None
    grid_locked: bool | None
    gold_frames: bool | None


class BuildRow(TypedDict):
    name: str
    boards: list[ParagonBoardModel]
    profile: str


@dataclass(slots=True)
class OverlayConfig:
    """Runtime configuration for overlay size, scaling, and persisted state."""

    cell_size: int = 24
    grid_x_default: int = PANEL_W + 24
    grid_y_default: int = 24

    cell_size_collapsed: int = 16
    grid_x_collapsed_default: int = 600
    grid_y_collapsed_default: int = 300

    ui_scale: float = 1.0
    panel_w: int = PANEL_W
    poll_ms: int = 250
    window_alpha: float = 0.86

    is_collapsed: bool = False
    grid_locked: bool = False
    gold_frames: bool = False
