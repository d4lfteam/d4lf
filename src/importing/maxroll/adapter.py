import json
import logging
from typing import TYPE_CHECKING, cast

from src.game_data import GameCatalog, ItemRarity, ItemType
from src.importing.contracts import ImportRequest, ImportResult, VariantMetadata
from src.importing.filters import (
    create_item_affix_pool,
    create_seal_charm_filter,
    is_unique_like_rarity,
    update_mingreateraffixcount,
)
from src.importing.maxroll.constants import BUILD_GUIDE_BASE_URL, PLANNER_API_DATA_URL, PLANNER_BASE_URL
from src.importing.maxroll.items import _find_item_affixes, _find_item_rarity
from src.importing.maxroll.paragon import extract_maxroll_paragon_steps
from src.importing.maxroll.planner import (
    _extract_planner_url_and_id_from_guide,
    _extract_planner_url_and_id_from_planner,
    _find_item_type,
    _find_legendary_aspect,
    _resolve_visible_profile_index,
    _unique_name_special_handling,
)
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.importing.web import get_with_retry, retry_importer
from src.perception import correct_name
from src.profiles import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel

if TYPE_CHECKING:
    from collections.abc import Mapping

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
type PlannerObject = dict[str, object]


def _planner_api_url(url: str) -> str:
    if BUILD_GUIDE_BASE_URL in url:
        api_url, _, _ = _extract_planner_url_and_id_from_guide(url)
    else:
        api_url, _, _ = _extract_planner_url_and_id_from_planner(url)
    return api_url


def _load_planner_data(url: str) -> tuple[dict[str, object], dict[str, object]]:
    """Fetch and decode planner data once for either discovery or import."""
    response = get_with_retry(url=_planner_api_url(url))
    all_data = cast("dict[str, object]", response.json())
    return all_data, cast("dict[str, object]", json.loads(str(all_data["data"])))


def _validated_url(request: ImportRequest) -> str | None:
    url = request.url
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return None
    return url


def fetch_variants_maxroll(request: ImportRequest) -> list[VariantMetadata]:
    if (url := _validated_url(request)) is None:
        return []
    LOGGER.info(f"Loading {url} for variants")
    try:
        all_data, build_data = _load_planner_data(url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return []
    variants: list[VariantMetadata] = []
    profiles = cast("list[PlannerObject]", build_data["profiles"])
    for profile_id, profile_data in enumerate(profiles):
        if profile_data.get("hidden"):
            continue
        variants.append(
            VariantMetadata(id=str(profile_id), name=str(profile_data.get("name") or f"Profile {profile_id + 1}"))
        )
    return variants


def _extract_profile_variant(
    *,
    profile_data: PlannerObject,
    items: dict[str, PlannerObject],
    mapping_data: dict[str, object],
    class_name: str,
    build_header: str,
    request: ImportRequest,
) -> Variant:
    variant_name = str(profile_data.get("name") or "")
    build_name = build_header or class_name
    if variant_name:
        build_name += f"_{variant_name}"

    finished_filters: list[ItemFilterModel] = []
    charm_filters: list[CharmFilterModel] = []
    seal_filters: list[SealFilterModel] = []
    aspect_upgrade_filters: list[str] = []
    item_mapping = cast("dict[str, dict[str, object]]", mapping_data["items"])
    item_type_mapping = cast("Mapping[str, Mapping[str, str]]", item_mapping)
    item_sets = cast("dict[str, dict[str, object]]", mapping_data.get("itemSets", {}))

    profile_items = cast("dict[str, object]", profile_data["items"])
    for item_id in profile_items.values():
        resolved_item = items[str(item_id)]
        resolved_item_id = str(resolved_item["id"])
        item_name = str(item_mapping[resolved_item_id]["name"])
        rarity = _find_item_rarity(resolved_item_id, mapping_data)
        is_unique_like = is_unique_like_rarity(rarity)

        item_filter = ItemFilterModel()
        if (
            item_type := _find_item_type(
                mapping_data=item_type_mapping, value=str(resolved_item["id"]), class_name=class_name
            )
        ) is None:
            LOGGER.warning(
                f"Couldn't find item type for {resolved_item['id']} from mapping data provided by Maxroll. Skipping item."
            )
            continue

        if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
            if "explicits" not in resolved_item:
                LOGGER.warning(
                    f"Maxroll is providing unreliable data for Seals/Charms, skipping a {item_type.value} for this build."
                )
                continue
            seal_charm_affixes = _find_item_affixes(
                mapping_data=mapping_data,
                item_affixes=cast("list[dict[str, object]]", resolved_item["explicits"]),
                item_type=item_type,
                import_greater_affixes=request.options.import_greater_affixes,
            )
            charm_or_seal_unique_aspect = None
            charm_set_name = None
            if is_unique_like:
                charm_or_seal_unique_aspect = correct_name(_unique_name_special_handling(item_name))
            elif rarity == ItemRarity.Set:
                set_key = str(item_mapping[resolved_item_id]["set"])
                charm_set_name = correct_name(str(item_sets[set_key]["name"]))
            if not seal_charm_affixes and not charm_or_seal_unique_aspect and not charm_set_name:
                LOGGER.warning(
                    f"Skipping {resolved_item.get('name', '(could not determine item name)')} because it had no supported affixes, unique aspect, or set name."
                )
                continue
            if item_type == ItemType.Charm:
                charm_filters.append(
                    create_seal_charm_filter(
                        affixes=seal_charm_affixes,
                        require_gas=request.options.require_greater_affixes,
                        model_type=CharmFilterModel,
                        unique_name=charm_or_seal_unique_aspect,
                        set_name=charm_set_name,
                    )
                )
            else:
                seal_filters.append(
                    create_seal_charm_filter(
                        affixes=seal_charm_affixes,
                        require_gas=request.options.require_greater_affixes,
                        model_type=SealFilterModel,
                        unique_name=charm_or_seal_unique_aspect,
                        set_name=charm_set_name,
                    )
                )
            continue

        item_filter.item_type = [item_type]
        if rarity == ItemRarity.Legendary and request.options.import_aspect_upgrades:
            legendary_aspect = _find_legendary_aspect(
                mapping_data,
                cast(
                    "dict[str, object] | list[object]",
                    resolved_item.get("legendaryPower", resolved_item.get("aspects", {})),
                ),
            )
            if legendary_aspect:
                if legendary_aspect not in GameCatalog().aspect_list:
                    LOGGER.warning(
                        f"Found legendary aspect '{legendary_aspect}' that is not in our aspect data, unable to add "
                        f"to AspectUpgrades. Please report a bug."
                    )
                else:
                    aspect_upgrade_filters.append(legendary_aspect)

        if is_unique_like:
            unique_name = item_name
            try:
                unique_name = _unique_name_special_handling(unique_name)
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=unique_name)]
            except Exception:
                LOGGER.exception(f"Unexpected error adding unique aspect for {unique_name}, please report a bug.")

        affixes = _find_item_affixes(
            mapping_data=mapping_data,
            item_affixes=cast("list[dict[str, object]]", resolved_item["explicits"]),
            item_type=item_type,
            import_greater_affixes=request.options.import_greater_affixes,
        )
        if affixes:
            item_filter.affix_pool = create_item_affix_pool(affixes=affixes, unique_like=is_unique_like)
            update_mingreateraffixcount(item_filter, request.options.require_greater_affixes)
        elif not item_filter.unique_aspect:
            LOGGER.warning(f"Skipping {item_name} because it had no supported affixes or unique aspect.")
            continue

        item_filter.min_power = 100
        finished_filters.append(item_filter)

    return Variant(
        name=variant_name,
        affix_filters=finished_filters,
        charm_filters=charm_filters,
        seal_filters=seal_filters,
        aspect_upgrade_filters=aspect_upgrade_filters,
        paragon_steps=extract_maxroll_paragon_steps(profile_data, mapping_data),
        paragon_build_name=build_name,
    )


@retry_importer
def import_maxroll(request: ImportRequest) -> ImportResult | None:
    if (url := _validated_url(request)) is None:
        return None
    LOGGER.info(f"Loading {url}")
    if BUILD_GUIDE_BASE_URL in url:
        _, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_guide(url)
    else:
        _, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_planner(url)
    try:
        all_data, build_data = _load_planner_data(url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return None
    guide_season = str(all_data.get("season", "") or "")
    profiles = cast("list[PlannerObject]", build_data["profiles"])
    items = cast("dict[str, PlannerObject]", build_data["items"])
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return None
    # The attribute descriptions are not always consistent with the casing for the key so we fix that here
    mapping_data["attributeDescriptions"] = {k.lower(): v for k, v in mapping_data["attributeDescriptions"].items()}
    class_name = str(all_data.get("class", "") or "")
    build_header = str(all_data.get("name", "") or class_name)
    finished_variants: list[Variant] = []
    selection = request.variant_selection

    profiles_to_extract = []
    if request.options.multi_build:
        for profile_id, profile_data in enumerate(profiles):
            if profile_data.get("hidden"):
                continue
            if selection is None or str(profile_id) in selection:
                profiles_to_extract.append((profile_id, profile_data))
    else:
        if build_id_is_visible_position:
            build_id = _resolve_visible_profile_index(profiles, build_id)
        profiles_to_extract.append((build_id, profiles[build_id]))

    for _profile_key, profile_data in profiles_to_extract:
        finished_variants.append(
            _extract_profile_variant(
                profile_data=profile_data,
                items=items,
                mapping_data=mapping_data,
                class_name=class_name,
                build_header=build_header,
                request=request,
            )
        )

    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="maxroll",
                class_name=class_name,
                build_header=build_header,
                season_number=guide_season,
                variants=finished_variants,
            ),
        ),
        request=request,
    )
