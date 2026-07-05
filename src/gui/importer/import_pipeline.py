import dataclasses
import logging
from typing import TYPE_CHECKING, Any, Protocol

from src.config.profile_document import ProfileDocumentStore
from src.config.profile_models import CharmFilterModel, ItemFilterModel, ProfileModel, SealFilterModel
from src.gui.importer.gui_common import (
    add_mythics_to_filters,
    add_to_profiles,
    build_default_profile_file_name,
    deduplicate_filters,
    sort_profile_filters,
)
from src.gui.importer.paragon_export import build_paragon_profile_payload

if TYPE_CHECKING:
    from src.gui.importer.importer_config import ImportConfig

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class Variant:
    name: str = ""
    affix_filters: list[ItemFilterModel] = dataclasses.field(default_factory=list)
    charm_filters: list[CharmFilterModel] = dataclasses.field(default_factory=list)
    seal_filters: list[SealFilterModel] = dataclasses.field(default_factory=list)
    aspect_upgrade_filters: list[str] = dataclasses.field(default_factory=list)
    mythic_names: list[str] = dataclasses.field(default_factory=list)
    paragon_steps: list[list[dict[str, Any]]] | None = None
    paragon_build_name: str = ""


@dataclasses.dataclass(slots=True)
class ExtractedBuild:
    source_name: str
    class_name: str
    build_header: str
    season_number: str = ""
    variants: list[Variant] = dataclasses.field(default_factory=list)


class BuildGuideAdapter(Protocol):
    url: str

    def extract(self) -> ExtractedBuild: ...


@dataclasses.dataclass(slots=True)
class StaticBuildGuideAdapter:
    url: str
    build: ExtractedBuild

    def extract(self) -> ExtractedBuild:
        return self.build


class ImportPipeline:
    @staticmethod
    def run(adapter: BuildGuideAdapter, config: ImportConfig) -> list[str]:
        build = adapter.extract()
        saved_file_names = []

        for index, variant in enumerate(build.variants):
            affix_filters = deduplicate_filters(list(variant.affix_filters))
            add_mythics_to_filters(list(variant.mythic_names), affix_filters)
            profile = ProfileModel(
                name="imported profile",
                Affixes=sort_profile_filters(affix_filters),
                Charms=sort_profile_filters(deduplicate_filters(variant.charm_filters)),
                Seals=sort_profile_filters(deduplicate_filters(variant.seal_filters)),
            )
            if config.import_aspect_upgrades and variant.aspect_upgrade_filters:
                profile.aspect_upgrades = variant.aspect_upgrade_filters

            file_name = config.custom_file_name or build_default_profile_file_name(
                source_name=build.source_name,
                class_name=build.class_name,
                season_number=build.season_number,
                build_header=build.build_header,
                variant_name=variant.name,
                filename_parts=config.filename_parts,
            )
            if config.custom_file_name and len(build.variants) > 1:
                file_name = f"{file_name}_{index + 1}"

            if config.export_paragon:
                if variant.paragon_steps:
                    profile.paragon = build_paragon_profile_payload(
                        build_name=variant.paragon_build_name or build.build_header or build.class_name,
                        source_url=adapter.url,
                        paragon_boards_list=variant.paragon_steps,
                    )
                else:
                    LOGGER.warning(
                        "Paragon export enabled, but no paragon data was found for %s variant %r.",
                        build.source_name,
                        variant.name or build.build_header or build.class_name,
                    )

            corrected_file_name = (
                ProfileDocumentStore
                .default()
                .save_new(file_name=file_name, profile=profile, source=adapter.url)
                .file_name
            )
            saved_file_names.append(corrected_file_name)

        if config.add_to_profiles:
            for saved_file_name in saved_file_names:
                add_to_profiles(saved_file_name)

        LOGGER.info("Finished")
        return saved_file_names
