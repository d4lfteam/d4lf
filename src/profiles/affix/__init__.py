"""Equipment affix profile editor interface."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.profiles.affix.dialogs import DeleteAffixPool
    from src.profiles.affix.group import AffixGroupEditor
    from src.profiles.affix.picker import ItemTypePicker
    from src.profiles.affix.pool import AffixPoolWidget
    from src.profiles.affix.tabs import AFFIXES_TABNAME, AffixesTab
    from src.profiles.affix.unique_aspect import UNIQUE_ASPECTS_TITLE, UniqueAspectWidget
    from src.profiles.affix.widget import AffixWidget

__all__ = [
    "AFFIXES_TABNAME",
    "UNIQUE_ASPECTS_TITLE",
    "AffixGroupEditor",
    "AffixPoolWidget",
    "AffixWidget",
    "AffixesTab",
    "DeleteAffixPool",
    "ItemTypePicker",
    "UniqueAspectWidget",
]

_LAZY_EXPORTS = {
    "AFFIXES_TABNAME": ("src.profiles.affix.tabs", "AFFIXES_TABNAME"),
    "AffixGroupEditor": ("src.profiles.affix.group", "AffixGroupEditor"),
    "DeleteAffixPool": ("src.profiles.affix.dialogs", "DeleteAffixPool"),
    "AffixPoolWidget": ("src.profiles.affix.pool", "AffixPoolWidget"),
    "AffixWidget": ("src.profiles.affix.widget", "AffixWidget"),
    "AffixesTab": ("src.profiles.affix.tabs", "AffixesTab"),
    "ItemTypePicker": ("src.profiles.affix.picker", "ItemTypePicker"),
    "UNIQUE_ASPECTS_TITLE": ("src.profiles.affix.unique_aspect", "UNIQUE_ASPECTS_TITLE"),
    "UniqueAspectWidget": ("src.profiles.affix.unique_aspect", "UniqueAspectWidget"),
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
