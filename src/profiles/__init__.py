"""Public profile capability interface.

Cross-capability callers import profile models, document persistence, and sessions
from this module.  The modules beneath this package are implementation details.
"""

from src.profiles._affixes import (
    AffixAspectFilterModel,
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    GlobalUniqueModel,
)
from src.profiles._document import (
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
from src.profiles._equipment import (
    CharmFilterModel,
    DynamicCharmFilterModel,
    DynamicItemFilterModel,
    DynamicSealFilterModel,
    ItemFilterModel,
    SealFilterModel,
)
from src.profiles._paragon import ParagonBoardModel, ParagonPayloadModel
from src.profiles._profile import ProfileModel
from src.profiles._session import (
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
from src.profiles._sigils import SigilConditionModel, SigilFilterModel, SigilPriority, TributeFilterModel

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
    "normalize_profile_file_name",
    "to_yaml_str",
]
