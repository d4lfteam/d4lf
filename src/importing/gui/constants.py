from dataclasses import dataclass

from src.importing import FilenamePart


@dataclass(frozen=True, slots=True)
class _CheckboxConfig:
    name: str
    label: str
    setting: str
    tooltip: str
    default: str
    fallbacks: tuple[str, ...] = ()


_CHECKBOX_CONFIGS = (
    _CheckboxConfig(
        name="import_aspect_upgrades_checkbox",
        label="Import Aspect Upgrades",
        setting="import_aspect_upgrades",
        tooltip="If legendary aspects are in the build, do you want an aspect upgrades section generated for them?",
        default="true",
    ),
    _CheckboxConfig(
        name="import_charms_checkbox",
        label="Import Charms",
        setting="import_charms",
        tooltip="If a build has charms, should they be included in the imported profile?",
        default="true",
    ),
    _CheckboxConfig(
        name="import_seals_checkbox",
        label="Import Seals",
        setting="import_seals",
        tooltip="If a build has seals, should they be included in the imported profile?",
        default="true",
    ),
    _CheckboxConfig(
        name="add_to_profiles_checkbox",
        label="Add to profiles",
        setting="add_to_profiles",
        tooltip="Do you want to add this build to your active profiles upon generating?",
        default="false",
        fallbacks=("import_add_to_profiles",),
    ),
    _CheckboxConfig(
        name="import_gas_checkbox",
        label="Include GAs",
        setting="import_greater_affixes",
        tooltip="Include the greater affix tags from the build, making it look for GAs?",
        default="false",
        fallbacks=("import_gas",),
    ),
    _CheckboxConfig(
        name="require_all_gas_checkbox",
        label="Require all GAs",
        setting="require_all_greater_affixes",
        tooltip="Are the GAs required to match the item?",
        default="false",
        fallbacks=("require_all_gas",),
    ),
    _CheckboxConfig(
        name="export_paragon_checkbox",
        label="Export Paragon",
        setting="export_paragon",
        tooltip="Export paragon boards for the paragon overlay?",
        default="false",
    ),
    _CheckboxConfig(
        name="multi_build_checkbox",
        label="Multi Build Import",
        setting="multi_build_import",
        tooltip="Import multiple builds from the link?",
        default="false",
    ),
)

INSTRUCTIONS_TEXT = (
    "You can link either the build guide or a direct link to the specific planner.\n\n"
    "https://maxroll.gg/d4/build-guides/tornado-druid-guide\n"
    "or\nhttps://maxroll.gg/d4/planner/cm6pf0xa#5\n"
    "or\nhttps://d4builds.gg/builds/ef414fbd-81cd-49d1-9c8d-4938b278e2ee\n"
    "or\nhttps://mobalytics.gg/diablo-4/builds/barbarian/bash\n"
    "or\nhttps://infinitybuilds.gg/en/builds/barbarian-fL8P6vVSqI\n\n"
    "It will create a file based on the label of the build in the planner in: "
    "{user_dir}\\profiles\n\n"
)

FILENAME_PART_LABELS = {
    FilenamePart.SOURCE: "Source",
    FilenamePart.SEASON: "Season",
    FilenamePart.CLASS: "Class",
    FilenamePart.BUILD_TITLE: "Build title",
    FilenamePart.VARIANT: "Variant",
}
GENERATE_DISABLED_FILENAME_PARTS_TOOLTIP = "Select at least one filename part or enter a custom file name."
IMPORTER_WINDOW_LOGGERS = (
    "src.importing.mobalytics",
    "src.importing.maxroll",
    "src.importing.d4builds",
    "src.importing.infinitybuilds",
    "src.importing.gui.support",
    "src.importing.pipeline",
    "src.profiles",
)
