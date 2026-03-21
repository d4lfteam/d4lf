from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImportVariantOption:
    id: str
    label: str


@dataclass
class ImportConfig:
    url: str
    import_uniques: bool
    import_aspect_upgrades: bool
    add_to_profiles: bool
    import_greater_affixes: bool
    require_greater_affixes: bool
    export_paragon: bool = False
    import_multiple_variants: bool = True
    selected_variants: tuple[str, ...] = ()
    custom_file_name: str | None = None
