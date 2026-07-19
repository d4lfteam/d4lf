"""Shared profile-editor infrastructure and composition."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.profiles.editor.profile import PROFILE_TABNAME, ProfileEditor, ProfileTab, _to_editor_tribute_filter
    from src.profiles.editor.window import ProfileEditorWindow

from src.profiles.editor.container import Container
from src.profiles.editor.dialogs import (
    DeleteItem,
    IgnoreScrollWheelComboBox,
    IgnoreScrollWheelSpinBox,
    MinGreaterDialog,
    MinPercentDialog,
    MinPowerDialog,
)
from src.profiles.editor.helpers import create_auto_sync_checkbox, create_readonly_line_edit, refresh_widget_style
from src.profiles.editor.pickers import CheckboxListDialog, RarityPicker, rarity_summary
from src.profiles.editor.rule_list import RuleListTab
from src.profiles.editor.session_store import QSettingsLastOpenedStore
from src.profiles.editor.tabs import TabGroupWidget

__all__ = [
    "PROFILE_TABNAME",
    "CheckboxListDialog",
    "Container",
    "DeleteItem",
    "IgnoreScrollWheelComboBox",
    "IgnoreScrollWheelSpinBox",
    "MinGreaterDialog",
    "MinPercentDialog",
    "MinPowerDialog",
    "ProfileEditor",
    "ProfileEditorWindow",
    "ProfileTab",
    "QSettingsLastOpenedStore",
    "RarityPicker",
    "RuleListTab",
    "TabGroupWidget",
    "_to_editor_tribute_filter",
    "create_auto_sync_checkbox",
    "create_readonly_line_edit",
    "rarity_summary",
    "refresh_widget_style",
]

_LAZY_EXPORTS = {
    "ProfileEditor": ("src.profiles.editor.profile", "ProfileEditor"),
    "_to_editor_tribute_filter": ("src.profiles.editor.profile", "_to_editor_tribute_filter"),
    "PROFILE_TABNAME": ("src.profiles.editor.profile", "PROFILE_TABNAME"),
    "ProfileTab": ("src.profiles.editor.profile", "ProfileTab"),
    "ProfileEditorWindow": ("src.profiles.editor.window", "ProfileEditorWindow"),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as error:
        message = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(message) from error
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
