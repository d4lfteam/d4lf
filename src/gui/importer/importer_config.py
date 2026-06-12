from dataclasses import dataclass


@dataclass
class ImportConfig:
    url: str
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_greater_affixes: bool
    export_paragon: bool = False
    custom_file_name: str | None = None
    filename_components: dict = None
