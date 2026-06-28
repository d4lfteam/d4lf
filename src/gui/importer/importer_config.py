from dataclasses import dataclass
from enum import StrEnum


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


@dataclass
class ImportConfig:
    url: str
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_greater_affixes: bool
    export_paragon: bool = False
    custom_file_name: str | None = None
    filename_parts: tuple[FilenamePart, ...] = DEFAULT_FILENAME_PARTS

    def __post_init__(self):
        self.filename_parts = tuple(FilenamePart(part) for part in self.filename_parts)
