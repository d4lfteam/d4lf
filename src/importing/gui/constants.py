from src.importing import FilenamePart

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
