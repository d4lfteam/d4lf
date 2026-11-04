"""Shared assets and Tk-thread primitives used by capability-owned desktop interfaces."""

from src.desktop.assets import DISCORD_ICON, GITHUB_ICON, ICON_PATH, get_asset_path
from src.desktop.overlay_contract import OverlayContract
from src.desktop.overlay_slot import OverlaySlot
from src.desktop.ui_thread import (
    call_on_ui_thread,
    create_overlay_toplevel,
    get_root,
    is_alive,
    join_ui_thread,
    post_to_ui_thread,
)

__all__ = [
    "DISCORD_ICON",
    "GITHUB_ICON",
    "ICON_PATH",
    "OverlayContract",
    "OverlaySlot",
    "call_on_ui_thread",
    "create_overlay_toplevel",
    "get_asset_path",
    "get_root",
    "is_alive",
    "join_ui_thread",
    "post_to_ui_thread",
]
