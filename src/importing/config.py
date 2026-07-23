from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.importing.contracts import DEFAULT_FILENAME_PARTS, FilenamePart

if TYPE_CHECKING:
    from src.importing.contracts import ImportRequest


@dataclass
class ImportConfig:
    url: str
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_greater_affixes: bool
    export_paragon: bool = False
    custom_file_name: str | None = None
    filename_parts: tuple[FilenamePart | str, ...] = DEFAULT_FILENAME_PARTS
    import_charms: bool = True
    import_seals: bool = True
    multi_build: bool = False

    @classmethod
    def from_request(cls, request: ImportRequest) -> ImportConfig:
        options = request.options
        return cls(
            url=request.url,
            import_aspect_upgrades=options.import_aspect_upgrades,
            import_charms=options.import_charms,
            import_seals=options.import_seals,
            add_to_profiles=options.add_to_profiles,
            import_greater_affixes=options.import_greater_affixes,
            require_greater_affixes=options.require_greater_affixes,
            export_paragon=options.export_paragon,
            multi_build=options.multi_build,
            custom_file_name=options.custom_file_name,
            filename_parts=request.filename_parts,
        )

    def __post_init__(self):
        self.filename_parts = tuple(FilenamePart(part) for part in self.filename_parts)
