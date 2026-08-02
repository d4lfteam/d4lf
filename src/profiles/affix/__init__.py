"""Equipment affix profile-editor interface."""

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
