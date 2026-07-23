import json
import logging

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
from src.item import Dataloader, ItemRarity, ItemType
from src.perception import correct_name
from src.profiles import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True


def fetch_variants_maxroll(request: ImportRequest) -> list[VariantMetadata]:
    url = request.url
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return []
    LOGGER.info(f"Loading {url} for variants")
    if BUILD_GUIDE_BASE_URL in url:
        api_url, _, _ = _extract_planner_url_and_id_from_guide(url)
    else:
        api_url, _, _ = _extract_planner_url_and_id_from_planner(url)
    try:
        r = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return []
    all_data = r.json()
    build_data = json.loads(all_data["data"])
    variants = []
    for profile_id, profile_data in enumerate(build_data["profiles"]):
        if profile_data.get("hidden"):
            continue
        variants.append(VariantMetadata(id=str(profile_id), name=profile_data["name"] or f"Profile {profile_id + 1}"))
    return variants


@retry_importer
def import_maxroll(request: ImportRequest, selected_variant_ids: list[str] | None = None) -> ImportResult | None:
    url = request.url
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return None
    LOGGER.info(f"Loading {url}")
    if BUILD_GUIDE_BASE_URL in url:
        api_url, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_guide(url)
    else:
        api_url, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_planner(url)
    try:
        r = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return None
    all_data = r.json()
    guide_season = all_data.get("season", "")
    build_data = json.loads(all_data["data"])
    if build_id_is_visible_position:
        build_id = _resolve_visible_profile_index(build_data["profiles"], build_id)
    items = build_data["items"]
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return None
    # The attribute descriptions are not always consistent with the casing for the key so we fix that here
    mapping_data["attributeDescriptions"] = {k.lower(): v for k, v in mapping_data["attributeDescriptions"].items()}
    active_profile = build_data["profiles"][build_id]
    build_header = all_data["name"] or all_data["class"]
    finished_variants: list[Variant] = []

    profiles_to_extract = []
    if request.options.multi_build:
        for profile_id, profile_data in enumerate(build_data["profiles"]):
            if profile_data.get("hidden"):
                continue
            if selected_variant_ids is None or str(profile_id) in selected_variant_ids:
                profiles_to_extract.append((profile_id, profile_data))
    else:
        profiles_to_extract.append((build_id, active_profile))

    for _profile_key, profile_data in profiles_to_extract:
        variant_name = profile_data["name"] or ""
        build_name = build_header
        if not build_name:
            build_name = all_data["class"]
        if variant_name:
            build_name += f"_{variant_name}"

        finished_filters: list[ItemFilterModel] = []
        charm_filters: list[CharmFilterModel] = []
        seal_filters: list[SealFilterModel] = []
        aspect_upgrade_filters: list[str] = []

        for item_id in profile_data["items"].values():
            resolved_item = items[str(item_id)]
            resolved_item_id = resolved_item["id"]
            item_name = mapping_data["items"][resolved_item_id]["name"]
            rarity = _find_item_rarity(resolved_item_id, mapping_data)
            is_unique_like = is_unique_like_rarity(rarity)

            item_filter = ItemFilterModel()
            if (
                item_type := _find_item_type(
                    mapping_data=mapping_data["items"], value=resolved_item["id"], class_name=all_data["class"]
                )
            ) is None:
                LOGGER.warning(
                    f"Couldn't find item type for {resolved_item['id']} from mapping data provided by Maxroll. Skipping item."
                )
                continue

            # TODO I don't think this code needs to be siloed, I think it can be mostly part of the normal flow so we're not repeating work. It'd just require some refactoring
            if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
                if "explicits" not in resolved_item:
                    LOGGER.warning(
                        f"Maxroll is providing unreliable data for Seals/Charms, skipping a {item_type.value} for this build."
                    )
                    continue
                seal_charm_affixes = _find_item_affixes(
                    mapping_data=mapping_data,
                    item_affixes=resolved_item["explicits"],
                    item_type=item_type,
                    import_greater_affixes=request.options.import_greater_affixes,
                )
                # Extract unique aspect and set info for charms
                charm_or_seal_unique_aspect = None
                charm_set_name = None
                if is_unique_like:
                    charm_or_seal_unique_aspect = correct_name(_unique_name_special_handling(item_name))
                elif rarity == ItemRarity.Set:
                    set_key = mapping_data["items"][resolved_item_id]["set"]
                    charm_set_name = correct_name(mapping_data["itemSets"][set_key]["name"])
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

            # Legendary aspect upgrade handling
            if rarity == ItemRarity.Legendary and request.options.import_aspect_upgrades:
                legendary_aspect = _find_legendary_aspect(
                    mapping_data, resolved_item.get("legendaryPower", resolved_item.get("aspects", {}))
                )
                if legendary_aspect:
                    if legendary_aspect not in Dataloader().aspect_list:
                        LOGGER.warning(
                            f"Found legendary aspect '{legendary_aspect}' that is not in our aspect data, unable to add "
                            f"to AspectUpgrades. Please report a bug."
                        )
                    else:
                        aspect_upgrade_filters.append(legendary_aspect)

            # Unique aspect, if the item is a unique or a mythic (mythics are functionally uniques, just purple)
            if is_unique_like:
                unique_name = item_name
                try:
                    unique_name = _unique_name_special_handling(unique_name)
                    item_filter.unique_aspect = [AspectUniqueFilterModel(name=unique_name)]
                except Exception:
                    LOGGER.exception(f"Unexpected error adding unique aspect for {unique_name}, please report a bug.")

            # Standard item handling
            affixes = _find_item_affixes(
                mapping_data=mapping_data,
                item_affixes=resolved_item["explicits"],
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
            # Match the other guide importers: let the shared pipeline deduplicate identical affix filters
            # instead of preserving duplicates via incrementing name suffixes.
            finished_filters.append(item_filter)

        finished_variants.append(
            Variant(
                name=variant_name,
                affix_filters=finished_filters,
                charm_filters=charm_filters,
                seal_filters=seal_filters,
                aspect_upgrade_filters=aspect_upgrade_filters,
                paragon_steps=extract_maxroll_paragon_steps(profile_data, mapping_data),
                paragon_build_name=build_name,
            )
        )

    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="maxroll",
                class_name=all_data["class"],
                build_header=build_header,
                season_number=guide_season,
                variants=finished_variants,
            ),
        ),
        request=request,
    )
