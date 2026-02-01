from dataclasses import dataclass


@dataclass
class ImportConfig:
    url: str
    import_uniques: bool
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_greater_affixes: bool
    export_paragon: bool
    custom_file_name: str | None
