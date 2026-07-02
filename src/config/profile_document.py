import datetime
import logging
import pathlib
import re
import shutil
from dataclasses import dataclass

import yaml
from pydantic import ValidationError
from ruamel.yaml import YAML, StringIO
from yaml import MappingNode, MarkedYAMLError

from src import __version__
from src.config.loader import IniConfigLoader
from src.config.profile_models import ProfileModel

LOGGER = logging.getLogger(__name__)


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep=False):
        mapping = set()
        for key_node, _ in node.value:
            if ":merge" in key_node.tag:
                continue
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise MarkedYAMLError(problem=f"Duplicate {key!r} key found in YAML", problem_mark=key_node.start_mark)
            mapping.add(key)
        return super().construct_mapping(node, deep)


class ProfileDocumentError(Exception):
    code = "profile_document_error"


class ProfileYamlError(ProfileDocumentError):
    code = "profile_yaml_error"


class EmptyProfileError(ProfileDocumentError):
    code = "empty_profile"


class ProfileValidationError(ProfileDocumentError):
    code = "profile_validation_error"

    def __init__(self, message: str, *, code: str | None = None, guidance: str = ""):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.guidance = guidance


@dataclass(frozen=True)
class LoadedProfile:
    path: pathlib.Path
    name: str
    profile: ProfileModel


@dataclass(frozen=True)
class SavedProfile:
    path: pathlib.Path
    file_name: str


@dataclass(frozen=True)
class ProfileDocumentStore:
    profiles_dir: pathlib.Path
    full_dump: bool

    @classmethod
    def default(cls) -> ProfileDocumentStore:
        config = IniConfigLoader()
        return cls(profiles_dir=config.user_dir / "profiles", full_dump=config.general.full_dump)

    def load(self, path: pathlib.Path | str) -> LoadedProfile:
        profile_path = pathlib.Path(path)
        profile_name = profile_path.stem.replace("_", " ")
        try:
            with profile_path.open(encoding="utf-8") as f:
                config = yaml.load(stream=f, Loader=UniqueKeyLoader)
        except yaml.YAMLError as exc:
            msg = f"Error in the YAML file {profile_path}: {exc}"
            raise ProfileYamlError(msg) from exc

        if config is None:
            msg = f"Empty YAML file {profile_path}, please remove it"
            raise EmptyProfileError(msg)
        if not isinstance(config, dict):
            msg = f"Profile document must be a YAML mapping: {profile_path}"
            raise ProfileValidationError(msg)

        try:
            profile = ProfileModel(name=profile_name, **config)
        except ValidationError as exc:
            raise _profile_validation_error(profile_path, exc) from exc

        LOGGER.info(f"File {profile_path} loaded.")
        return LoadedProfile(path=profile_path, name=profile_name, profile=profile)

    def save_existing(
        self, *, loaded: LoadedProfile, profile: ProfileModel, source: str, backup_original: bool = False
    ) -> SavedProfile:
        save_path = loaded.path
        if save_path.exists() and backup_original:
            backup_path = self.profiles_dir / "backups" / f"{save_path.stem}_original.yaml"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            if not backup_path.exists():
                shutil.copyfile(save_path, backup_path)
        return self._write_profile(save_path=save_path, profile=profile, source=source, exclude={"name"})

    def save_new(self, *, file_name: str, profile: ProfileModel, source: str) -> SavedProfile:
        normalized_file_name = normalize_profile_file_name(file_name)
        save_path = self.profiles_dir / f"{normalized_file_name}.yaml"
        return self._write_profile(save_path=save_path, profile=profile, source=source)

    def _write_profile(
        self, *, save_path: pathlib.Path, profile: ProfileModel, source: str, exclude: set[str] | None = None
    ) -> SavedProfile:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        exclude = exclude or {"name", "Sigils"}
        with save_path.open("w", encoding="utf-8") as file:
            file.write(f"# {source}\n")
            file.write(f"# {datetime.datetime.now(tz=datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')} (v{__version__})\n")
            file.write(to_yaml_str(profile, exclude_defaults=not self.full_dump, exclude=exclude))
        LOGGER.info(f"Created profile {save_path}")
        return SavedProfile(path=save_path, file_name=save_path.stem)


def normalize_profile_file_name(file_name: str) -> str:
    file_name = file_name.replace("'", "")
    file_name = re.sub(r"\W", "_", file_name)
    return re.sub(r"_+", "_", file_name).rstrip("_")


def to_yaml_str(profile: ProfileModel, exclude_defaults: bool, exclude: set[str]) -> str:
    str_val = profile.model_dump_json(
        by_alias=False, exclude_defaults=exclude_defaults, exclude_none=True, exclude=exclude
    )
    yaml_writer = YAML()
    yaml_writer.default_flow_style = None
    dict_val = yaml_writer.load(str_val)
    if "paragon" in dict_val:
        dict_val["Paragon"] = dict_val.pop("paragon")
    _sort_profile_sections(dict_val)
    _rm_style_info(dict_val)
    _use_block_style(dict_val)
    stream = StringIO()
    yaml_writer.dump(dict_val, stream)
    stream.seek(0)
    return stream.read()


def _profile_validation_error(profile_path: pathlib.Path, exc: ValidationError) -> ProfileValidationError:
    if "minGreaterAffixCount" in str(exc):
        return ProfileValidationError(
            f"Profile validation failed: {profile_path}",
            code="pool_min_greater_affix_count_legacy",
            guidance=_legacy_min_greater_affix_count_guidance(profile_path),
        )
    return ProfileValidationError(f"Validation error in {profile_path}:\n\n{exc}")


def _legacy_min_greater_affix_count_guidance(profile_path: pathlib.Path) -> str:
    return (
        f"PROFILE VALIDATION FAILED: {profile_path}\n\n"
        "You are using an old, outdated field that must be removed from your profile.\n\n"
        "WRONG (old way - pool level):\n"
        "- Ring:\n"
        "    itemType: [ring]\n"
        "    minPower: 100\n"
        "    affixPool:\n"
        "    - count:\n"
        "      - {name: strength}\n"
        "      minCount: 2\n"
        "      minGreaterAffixCount: 1  <- DELETE THIS LINE\n\n"
        "CORRECT (new way - item level):\n"
        "- Ring:\n"
        "    itemType: [ring]\n"
        "    minPower: 100\n"
        "    minGreaterAffixCount: 1  <- PUT IT HERE INSTEAD\n"
        "    affixPool:\n"
        "    - count:\n"
        "      - {name: strength}\n"
        "      minCount: 2\n"
        "      # NO minGreaterAffixCount here anymore!\n\n"
        f"ACTION REQUIRED: Please make the above adjustments in:\n{profile_path}"
    )


def _sort_profile_sections(d):
    if not isinstance(d, dict):
        return

    for key in ("aspect_upgrades", "AspectUpgrades"):
        if isinstance(d.get(key), list):
            d[key].sort(key=str.casefold)
            break


def _use_block_style(d):
    if not isinstance(d, dict):
        return

    for key in ("aspect_upgrades", "AspectUpgrades"):
        if hasattr(d.get(key), "fa"):
            d[key].fa.set_block_style()
            break


def _rm_style_info(d):
    if isinstance(d, dict):
        d.fa._flow_style = None
        for k, v in d.items():
            _rm_style_info(k)
            _rm_style_info(v)
    elif isinstance(d, list):
        d.fa._flow_style = None
        for elem in d:
            _rm_style_info(elem)
