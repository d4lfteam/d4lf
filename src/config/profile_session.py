import copy
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from src.config.loader import IniConfigLoader
from src.config.profile_document import (
    EmptyProfileError,
    LoadedProfile,
    ProfileDocumentStore,
    ProfileValidationError,
    ProfileYamlError,
    SavedProfile,
)
from src.config.profile_models import ProfileModel

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path


class ProfileLastOpenedStore(Protocol):
    def get(self) -> str | None: ...

    def set(self, name: str) -> None: ...


class _NoopLastOpenedStore:
    def __init__(self) -> None:
        self._name: str | None = None

    def get(self) -> str | None:
        return self._name

    def set(self, name: str) -> None:
        self._name = name


@dataclass(frozen=True)
class ProfileCatalog:
    active: list[str]
    inactive: list[str]
    paths: dict[str, Path]


@dataclass(frozen=True)
class Loaded:
    loaded_profile: LoadedProfile


@dataclass(frozen=True)
class YamlError:
    message: str


@dataclass(frozen=True)
class EmptyError:
    message: str


@dataclass(frozen=True)
class ValidationError:
    message: str
    guidance: str = ""


LoadResult = Loaded | YamlError | EmptyError | ValidationError


@dataclass(frozen=True)
class Saved:
    saved: SavedProfile


@dataclass(frozen=True)
class ValidationDiffers:
    coerced_model: ProfileModel


@dataclass(frozen=True)
class Failed:
    error: Exception


SaveResult = Saved | ValidationDiffers | Failed


class ProfileSession:
    def __init__(
        self,
        *,
        document_store: ProfileDocumentStore | None = None,
        last_opened_store: ProfileLastOpenedStore | None = None,
    ) -> None:
        self._document_store = document_store or ProfileDocumentStore.default()
        self._last_opened_store = last_opened_store or _NoopLastOpenedStore()
        self._loaded_profile: LoadedProfile | None = None
        self._loaded_snapshot: ProfileModel | None = None

    def discover(self) -> ProfileCatalog:
        profiles_dir = self._document_store.profiles_dir
        profiles_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            profile_file.stem: profile_file
            for profile_file in profiles_dir.iterdir()
            if profile_file.is_file() and profile_file.suffix.lower() in {".yaml", ".yml"}
        }

        active: list[str] = []
        for profile_name in IniConfigLoader().general.profiles:
            if profile_name in paths and profile_name not in active:
                active.append(profile_name)

        inactive = sorted((profile_name for profile_name in paths if profile_name not in active), key=str.lower)
        return ProfileCatalog(active=active, inactive=inactive, paths=paths)

    def last_opened_profile(self) -> str | None:
        return self._last_opened_store.get()

    def load(self, name: str) -> LoadResult:
        catalog = self.discover()
        profile_path = catalog.paths.get(name)
        if profile_path is None:
            return ValidationError(message=f"Profile not found: {name}")

        try:
            loaded_profile = self._document_store.load(profile_path)
        except ProfileYamlError as error:
            return YamlError(message=str(error))
        except EmptyProfileError as error:
            return EmptyError(message=str(error))
        except ProfileValidationError as error:
            return ValidationError(message=str(error), guidance=error.guidance)

        self._loaded_profile = loaded_profile
        self._loaded_snapshot = copy.deepcopy(loaded_profile.profile)
        self._last_opened_store.set(name)
        return Loaded(loaded_profile=loaded_profile)

    def save(self, profile_model: ProfileModel, *, force: bool = False) -> SaveResult:
        if self._loaded_profile is None:
            return Failed(error=RuntimeError("No profile loaded"))

        try:
            validated_model = ProfileModel.model_validate(profile_model.model_dump(mode="python", by_alias=True))
            if validated_model != profile_model and not force:
                return ValidationDiffers(coerced_model=validated_model)
            saved = self._document_store.save_existing(
                loaded=self._loaded_profile, profile=validated_model, source="custom", backup_original=True
            )
        except Exception as error:
            LOGGER.exception("Failed to save profile")
            return Failed(error=error)

        self._loaded_profile = LoadedProfile(
            path=self._loaded_profile.path, name=self._loaded_profile.name, profile=validated_model
        )
        self._loaded_snapshot = copy.deepcopy(validated_model)
        return Saved(saved=saved)

    def is_dirty(self, current_profile_model: ProfileModel) -> bool:
        if self._loaded_snapshot is None:
            return False
        return current_profile_model != self._loaded_snapshot
