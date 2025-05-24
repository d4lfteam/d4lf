from dataclasses import dataclass


@dataclass
class ImportConfig:
    url: str
    import_uniques: bool
    import_aspect_upgrades: bool
    add_to_profiles: bool
    custom_file_name: str | None
