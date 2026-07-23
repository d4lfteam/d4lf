import dataclasses
import logging
from typing import Any, Protocol, TypeVar

from src.importing import ImportRequest, ImportResult, assemble_profile_file_name
from src.importing.filters import deduplicate_filters, sort_profile_filters
from src.importing.paragon import build_paragon_profile_payload
from src.importing.profiles import add_to_profiles
from src.profiles import CharmFilterModel, ItemFilterModel, ProfileDocumentStore, ProfileModel, SealFilterModel

LOGGER = logging.getLogger(__name__)
FilterModelT = TypeVar("FilterModelT", CharmFilterModel, SealFilterModel)


@dataclasses.dataclass(slots=True)
class Variant:
    name: str = ""
    affix_filters: list[ItemFilterModel] = dataclasses.field(default_factory=list)
    affix_filter_name_hints: list[str | None] = dataclasses.field(default_factory=list)
    charm_filters: list[CharmFilterModel] = dataclasses.field(default_factory=list)
    seal_filters: list[SealFilterModel] = dataclasses.field(default_factory=list)
    aspect_upgrade_filters: list[str] = dataclasses.field(default_factory=list)
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


def _enabled_category_filters(filters: list[FilterModelT], enabled: bool) -> list[dict[str, FilterModelT]]:
    return sort_profile_filters(deduplicate_filters(filters)) if enabled else []


class ImportPipeline:
    @staticmethod
    def run(adapter: BuildGuideAdapter, request: ImportRequest) -> list[str]:
        return list(ImportPipeline.run_result(adapter, request).saved_file_names)

    @staticmethod
    def run_result(adapter: BuildGuideAdapter, request: ImportRequest) -> ImportResult:
        """Normalize, persist, and return the result of an extracted build."""
        build = adapter.extract()
        options = request.options
        saved_file_names: list[str] = []
        selected_profile = ProfileModel(name="imported profile")
        selected_variant = ""
        selected_paragon = None

        for index, variant in enumerate(build.variants):
            affix_filters = deduplicate_filters(
                list(variant.affix_filters), name_hints=variant.affix_filter_name_hints or None
            )
            profile = ProfileModel(
                name="imported profile",
                Affixes=sort_profile_filters(affix_filters),
                Charms=_enabled_category_filters(variant.charm_filters, options.import_charms),
                Seals=_enabled_category_filters(variant.seal_filters, options.import_seals),
            )
            if options.import_aspect_upgrades and variant.aspect_upgrade_filters:
                profile.aspect_upgrades = variant.aspect_upgrade_filters

            file_name = options.custom_file_name or assemble_profile_file_name(
                source_name=build.source_name,
                class_name=build.class_name,
                season_number=build.season_number,
                build_header=build.build_header,
                variant_name=variant.name,
                filename_parts=options.filename_parts,
            )
            if options.custom_file_name and len(build.variants) > 1:
                file_name = f"{file_name}_{index + 1}"

            if options.export_paragon:
                if variant.paragon_steps:
                    profile.paragon = build_paragon_profile_payload(
                        build_name=variant.paragon_build_name or build.build_header or build.class_name,
                        source_url=request.url,
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
            if index == 0:
                selected_profile = profile
                selected_variant = variant.name
                selected_paragon = profile.paragon

        if options.add_to_profiles:
            for saved_file_name in saved_file_names:
                add_to_profiles(saved_file_name)

        LOGGER.info("Finished")
        return ImportResult(
            source_name=build.source_name,
            selected_variant=selected_variant,
            profile=selected_profile,
            paragon=selected_paragon,
            saved_file_name=saved_file_names[0] if saved_file_names else None,
            saved_file_names=tuple(saved_file_names),
        )
