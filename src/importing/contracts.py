import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, cast

from src.profiles import ParagonPayloadModel, ProfileModel, normalize_profile_file_name


class FilenamePart(StrEnum):
    SOURCE = "source"
    SEASON = "season"
    CLASS = "class"
    BUILD_TITLE = "build_title"
    VARIANT = "variant"


DEFAULT_FILENAME_PARTS = (
    FilenamePart.SOURCE,
    FilenamePart.SEASON,
    FilenamePart.CLASS,
    FilenamePart.BUILD_TITLE,
    FilenamePart.VARIANT,
)


@dataclass(frozen=True, slots=True)
class ImportOptions:
    """Options that affect conversion and persistence, independent of a URL."""

    import_aspect_upgrades: bool = True
    import_charms: bool = True
    import_seals: bool = True
    add_to_profiles: bool = False
    import_greater_affixes: bool = False
    require_greater_affixes: bool = False
    export_paragon: bool = False
    custom_file_name: str | None = None
    filename_parts: tuple[FilenamePart | str, ...] = DEFAULT_FILENAME_PARTS

    def __post_init__(self) -> None:
        object.__setattr__(self, "filename_parts", tuple(FilenamePart(part) for part in self.filename_parts))
        if self.custom_file_name:
            object.__setattr__(self, "custom_file_name", self.custom_file_name.split(".", 1)[0].strip() or None)


@dataclass(frozen=True, slots=True)
class ImportRequest:
    url: str
    options: ImportOptions = field(default_factory=ImportOptions)

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", self.url.strip().replace("\n", ""))

    @property
    def filename_parts(self) -> tuple[FilenamePart, ...]:
        return cast("tuple[FilenamePart, ...]", self.options.filename_parts)


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Normalized output of one source import."""

    source_name: str
    selected_variant: str
    profile: ProfileModel
    paragon: ParagonPayloadModel | None = None
    saved_file_name: str | None = None
    saved_file_names: tuple[str, ...] = ()


class ImportSource(Protocol):
    @property
    def name(self) -> str: ...

    def import_build(self, request: ImportRequest) -> ImportResult: ...


def assemble_profile_file_name(
    *,
    source_name: str,
    class_name: str = "",
    season_number: str = "",
    build_header: str = "",
    variant_name: str = "",
    filename_parts: tuple[FilenamePart | str, ...] = DEFAULT_FILENAME_PARTS,
) -> str:
    """Build the stable profile filename used by all importing sources."""
    selected = {FilenamePart(part) for part in filename_parts}
    source = _normalize_name_part(source_name) or "imported"
    title = _clean_build_header(source, build_header, season_number)
    class_name = _normalize_name_part(class_name) or "unknown"
    variant = _normalize_name_part(variant_name)
    season_match = re.search(r"\d+", str(season_number))
    season = f"s{season_match.group(0)}" if season_match else ""
    parts: list[str] = []
    if FilenamePart.SOURCE in selected:
        parts.append(source)
    if FilenamePart.SEASON in selected and season:
        parts.append(season)
    if FilenamePart.CLASS in selected:
        parts.append(class_name)
    if FilenamePart.BUILD_TITLE in selected and title:
        parts.append(title)
    if FilenamePart.VARIANT in selected and variant:
        parts.append(variant)
    return normalize_profile_file_name("_".join(parts)) or "imported"


_SOURCE_TITLE_SUFFIXES = {
    "d4builds": ("D4Builds", "D4 Builds"),
    "infinitybuilds": ("InfinityBuilds", "Infinity Builds"),
    "maxroll": ("Maxroll",),
    "mobalytics": ("Mobalytics",),
}


def _clean_build_header(source_name: str, build_header: str, season_number: str) -> str:
    clean = _normalize_name_part(build_header)
    if not clean:
        return ""
    for label in _SOURCE_TITLE_SUFFIXES.get(source_name, (source_name.title(),)):
        for separator in (" - ", " | ", " · "):
            if clean.endswith(f"{separator}{label.casefold()}"):
                clean = clean.removesuffix(f"{separator}{label.casefold()}")
                break
    if re.search(r"\d+", str(season_number)):
        clean = re.sub(r"^\s*(?:S\d+|Season\s+\d+)\b", "", clean, count=1, flags=re.IGNORECASE)
        clean = re.sub(r"\(\s*(?:S\d+|Season\s+\d+)\s*\)", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\b(?:S\d+|Season\s+\d+)\b", "", clean, flags=re.IGNORECASE)
    return _normalize_name_part(clean)


def _normalize_name_part(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()
