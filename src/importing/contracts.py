import re
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Protocol, cast, runtime_checkable

from src.profiles import ParagonPayloadModel, ProfileModel, normalize_profile_file_name


class ImportSourceError(Exception):
    """Expected failure raised while reading a supported import source."""


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
    multi_build: bool = False
    custom_file_name: str | None = None
    filename_parts: tuple[FilenamePart | str, ...] = DEFAULT_FILENAME_PARTS

    def __post_init__(self) -> None:
        object.__setattr__(self, "filename_parts", tuple(FilenamePart(part) for part in self.filename_parts))
        if self.custom_file_name:
            object.__setattr__(self, "custom_file_name", self.custom_file_name.split(".", 1)[0].strip() or None)


@dataclass(frozen=True, slots=True)
class VariantSelection:
    """Immutable provider selection carried by an import request."""

    ids: tuple[str, ...]

    @classmethod
    def from_ids(cls, ids: VariantSelection | tuple[str, ...]) -> VariantSelection:
        if isinstance(ids, cls):
            return ids
        return cls(cast("tuple[str, ...]", ids))

    def __contains__(self, value: object) -> bool:
        return value in self.ids

    def __bool__(self) -> bool:
        return bool(self.ids)


@dataclass(frozen=True, slots=True)
class ImportRequest:
    url: str
    options: ImportOptions = field(default_factory=ImportOptions)
    variant_selection: VariantSelection | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", self.url.strip().replace("\n", ""))
        if self.variant_selection is not None and not isinstance(self.variant_selection, VariantSelection):
            message = "variant_selection must be a VariantSelection"
            raise TypeError(message)

    @property
    def filename_parts(self) -> tuple[FilenamePart, ...]:
        return cast("tuple[FilenamePart, ...]", self.options.filename_parts)

    def with_variant_selection(self, selection: VariantSelection | tuple[str, ...]) -> ImportRequest:
        return replace(self, variant_selection=VariantSelection.from_ids(selection))


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Normalized output of one source import."""

    source_name: str
    selected_variant: str
    profile: ProfileModel
    paragon: ParagonPayloadModel | None = None
    saved_file_name: str | None = None
    saved_file_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VariantMetadata:
    id: str
    name: str


class ImportSource(Protocol):
    @property
    def name(self) -> str: ...

    def fetch_variants(self, request: ImportRequest) -> list[VariantMetadata]: ...

    def import_build(self, request: ImportRequest) -> ImportResult: ...


@runtime_checkable
class ClosableImportSource(Protocol):
    """Optional lifecycle capability implemented by stateful sources."""

    def close(self) -> None: ...


class ImportSession:
    """Own one source instance for a complete discovery/import lifecycle.

    Source adapters that do not own resources need no special support: their
    session cleanup is a no-op. Stateful adapters can expose ``close`` and are
    guaranteed one idempotent call when the session ends.
    """

    __slots__ = ("_closed", "_source")

    def __init__(self, source: ImportSource) -> None:
        self._source = source
        self._closed = False

    @property
    def source(self) -> ImportSource:
        """Exact source instance retained by this session."""
        return self._source

    @property
    def name(self) -> str:
        return self._source.name

    @property
    def closed(self) -> bool:
        return self._closed

    def fetch_variants(self, request: ImportRequest) -> list[VariantMetadata]:
        return self._source.fetch_variants(request)

    def import_build(self, request: ImportRequest) -> ImportResult:
        return self._source.import_build(request)

    def close(self) -> None:
        """Release source-owned state exactly once."""
        if self._closed:
            return
        self._closed = True
        if isinstance(self._source, ClosableImportSource):
            self._source.close()


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
