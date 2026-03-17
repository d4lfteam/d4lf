from dataclasses import dataclass


@dataclass(slots=True)
class ImportConfig:
    """Holds the import settings shared by all importer backends."""

    url: str
    import_uniques: bool
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_greater_affixes: bool
    export_paragon: bool = False
    custom_file_name: str | None = None
    # Maxroll variant selection is performed in the GUI thread before the worker starts.
    selected_profile_indices: list[int] | None = None
