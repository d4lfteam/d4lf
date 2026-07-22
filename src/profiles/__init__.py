"""Public profile capability interface.

Cross-capability callers import profile models, document persistence, and sessions
from this module.  The modules beneath this package are implementation details.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

from src.profiles.affixes import (
    AffixAspectFilterModel,
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    GlobalUniqueModel,
)
from src.profiles.document import (
    EmptyProfileError,
    LoadedProfile,
    ProfileDocumentError,
    ProfileDocumentStore,
    ProfileValidationError,
    ProfileYamlError,
    SavedProfile,
    normalize_profile_file_name,
    to_yaml_str,
)
from src.profiles.equipment import (
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicItemFilterModel,
    DynamicSealFilterModel,
    ItemFilterModel,
    SealFilterModel,
)
from src.profiles.paragon import ParagonBoardModel, ParagonPayloadModel
from src.profiles.profile import ProfileModel
from src.profiles.session import (
    EmptyError,
    Failed,
    Loaded,
    LoadResult,
    ProfileCatalog,
    ProfileLastOpenedStore,
    ProfileSession,
    Saved,
    SaveResult,
    ValidationDiffers,
    ValidationError,
    YamlError,
)
from src.profiles.sigils import SigilConditionModel, SigilFilterModel, SigilPriority, TributeFilterModel


def create_profile_editor_window(
    parent: QWidget | None = None, profile_name: str | None = None, force_maximized: bool = False
) -> object:
    """Create the profile capability's standalone editor window."""
    from src.profiles.editor import ProfileEditorWindow  # ruff:ignore[import-outside-top-level]

    return ProfileEditorWindow(parent=parent, profile_name=profile_name, force_maximized=force_maximized)


__all__ = [
    "AffixAspectFilterModel",
    "AffixFilterCountModel",
    "AffixFilterModel",
    "AspectUniqueFilterModel",
    "CharmFilterModel",
    "DynamicCharmFilterModel",
    "DynamicItemFilterModel",
    "DynamicSealFilterModel",
    "EmptyError",
    "EmptyProfileError",
    "Failed",
    "GlobalUniqueModel",
    "ItemFilterModel",
    "LoadResult",
    "Loaded",
    "LoadedProfile",
    "ParagonBoardModel",
    "ParagonPayloadModel",
    "ProfileCatalog",
    "ProfileDocumentError",
    "ProfileDocumentStore",
    "ProfileLastOpenedStore",
    "ProfileModel",
    "ProfileSession",
    "ProfileValidationError",
    "ProfileYamlError",
    "SaveResult",
    "Saved",
    "SavedProfile",
    "SealFilterModel",
    "SigilConditionModel",
    "SigilFilterModel",
    "SigilPriority",
    "TributeFilterModel",
    "ValidationDiffers",
    "ValidationError",
    "YamlError",
    "create_profile_editor_window",
    "normalize_profile_file_name",
    "to_yaml_str",
]
