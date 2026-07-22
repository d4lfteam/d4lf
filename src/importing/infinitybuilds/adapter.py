import logging
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.importing.config import ImportConfig
from src.importing.conversion import as_string_keyed_mapping as _as_object
from src.importing.filters import (
    create_item_affix_pool,
    create_seal_charm_filter,
    is_unique_like_rarity,
    match_to_enum,
    update_mingreateraffixcount,
)
from src.importing.infinitybuilds.extraction import (
    _canonical_catalog_id,
    _convert_raw_to_affixes,
    _extract_build_data,
    _extract_build_title,
    _normalize_aspect_name,
    _parse_gear_piece,
    _resolve_gear_data,
)
from src.importing.infinitybuilds.paragon import (
    InfinityBuildsParagonCatalog,
    extract_infinitybuilds_paragon_steps,
    fetch_infinitybuilds_paragon_catalog,
)
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.importing.web import retry_importer
from src.item import Dataloader, ItemType
from src.profiles import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing import ImportRequest, ImportResult
    from src.importing.infinitybuilds.models import _ResolvedGearData
LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://infinitybuilds.gg/"
SCRIPT_XPATH = "//script"
ASPECT_UPGRADE_RARITIES = {"legendary"}


class InfinityBuildsError(Exception):
    pass


def import_infinitybuilds(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    return _import_infinitybuilds(ImportConfig.from_request(request), driver)


@retry_importer(inject_webdriver=True)
def _import_infinitybuilds(config: ImportConfig, driver: WebDriver | None = None) -> ImportResult | None:
    if driver is None:
        msg = "A Selenium WebDriver is required for InfinityBuilds imports"
        raise RuntimeError(msg)
    url = config.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use an infinitybuilds.gg build link")
        return None
    LOGGER.info(f"Loading {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    # The build data is streamed in via React Server Components after initial hydration, so wait
    # for it to actually show up in the page source instead of just the first script tag. Note the
    # embedded JSON is itself JSON-string-encoded, so quotes appear escaped (\"classId\") here.
    wait.until(lambda d: "classId" in d.page_source and "variants" in d.page_source)
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)
    build_header = _extract_build_title(raw_html_data)
    build_data = _extract_build_data(raw_html_data)
    if build_data is None:
        LOGGER.error(
            msg := "No script containing build data was found. This means InfinityBuilds has changed how they "
            "present data, please submit a bug."
        )
        raise InfinityBuildsError(msg)
    class_name = build_data.get("classId", "")
    if not class_name:
        LOGGER.error(msg := "No class name found")
        raise InfinityBuildsError(msg)
    variants = build_data.get("variants") or []
    variants = [v for v in variants if v.get("gear")]
    if not variants:
        LOGGER.error(msg := "No gear found for this build")
        raise InfinityBuildsError(msg)
    # InfinityBuilds URLs don't let you pick a specific variant, so import all of them
    if len(variants) > 1:
        LOGGER.info(f"This build has {len(variants)} variants, importing all of them.")
    # Resolve all variants' gear in a single API call to avoid redundant round trips.
    resolved = _resolve_gear_data(class_name, [piece for variant in variants for piece in variant["gear"]])
    paragon_catalog: InfinityBuildsParagonCatalog | None = None
    if config.export_paragon:
        try:
            paragon_catalog = fetch_infinitybuilds_paragon_catalog()
        except TypeError, ValueError:
            LOGGER.warning(
                "Could not fetch InfinityBuilds paragon catalog data, skipping paragon export.", exc_info=True
            )
    extracted_variants = []
    for variant in variants:
        extracted_variant = _build_variant_for_gear(gear=variant["gear"], resolved=resolved, config=config)
        extracted_variant.name = variant.get("name", "")
        if paragon_catalog is not None:
            extracted_variant.paragon_steps = extract_infinitybuilds_paragon_steps(
                variant.get("paragon") or {}, paragon_catalog, class_name
            )
        extracted_variant.paragon_build_name = build_header or extracted_variant.name
        extracted_variants.append(extracted_variant)
    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="infinitybuilds",
                class_name=class_name,
                build_header=build_header,
                variants=extracted_variants,
            ),
        ),
        config=config,
    )


def _build_variant_for_gear(
    gear: Sequence[Mapping[str, object]], resolved: _ResolvedGearData, config: ImportConfig
) -> Variant:
    finished_filters: list[ItemFilterModel] = []
    charm_filters: list[CharmFilterModel] = []
    seal_filters: list[SealFilterModel] = []
    aspect_upgrade_filters: list[str] = []
    for raw_gear_piece in gear:
        gear_piece = _parse_gear_piece(_as_object(raw_gear_piece))
        item_id = _canonical_catalog_id(gear_piece.get("itemId"))
        item = resolved.items.get(item_id, {})
        item_name = item.get("label", "")
        if not item_name:
            LOGGER.warning(f"Skipping {gear_piece.get('slot')} because no item name was resolved.")
            continue
        rarity = item.get("rarity", "")
        is_unique_like = is_unique_like_rarity(rarity)
        # Use the resolved catalog slot name (e.g. "Sword", "Ring", "Chest Armor") rather than the
        # build's internal slot key (e.g. "mainhand", "ring1", "chest") which doesn't map 1:1.
        catalog_slot = item.get("slot", "")
        item_type = match_to_enum(ItemType, catalog_slot)
        if item_type is None:
            LOGGER.warning(f"Couldn't match item_type for slot {catalog_slot!r}. Please edit manually")
        aspect_id = _canonical_catalog_id(gear_piece.get("aspectId"))
        aspect_name = resolved.aspects.get(aspect_id, {}).get("label") if aspect_id else None
        if aspect_name and rarity in ASPECT_UPGRADE_RARITIES and config.import_aspect_upgrades:
            normalized_aspect_name = _normalize_aspect_name(aspect_name)
            if normalized_aspect_name in Dataloader().aspect_list:
                aspect_upgrade_filters.append(normalized_aspect_name)
            else:
                LOGGER.warning(
                    f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
                )
        affixes = _convert_raw_to_affixes(
            gear_piece.get("affixes") or [], resolved.affixes, config.import_greater_affixes, item_type=item_type
        )
        if item_type == ItemType.Charm:
            unique_name = item_name if is_unique_like else None
            if not affixes and not unique_name:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes or unique aspect.")
                continue
            charm_filters.append(
                create_seal_charm_filter(
                    affixes=affixes,
                    require_gas=config.require_greater_affixes,
                    model_type=CharmFilterModel,
                    unique_name=unique_name,
                )
            )
            continue
        if item_type == ItemType.HoradricSeal:
            unique_name = item_name if is_unique_like else None
            if not affixes and not unique_name:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes or unique aspect.")
                continue
            seal_filters.append(
                create_seal_charm_filter(
                    affixes=affixes,
                    require_gas=config.require_greater_affixes,
                    model_type=SealFilterModel,
                    unique_name=unique_name,
                )
            )
            continue
        item_filter = ItemFilterModel()
        item_filter.item_type = [item_type] if item_type else []
        if is_unique_like:
            item_filter.unique_aspect = [AspectUniqueFilterModel(name=item_name)]
        if not affixes and not item_filter.unique_aspect:
            LOGGER.warning(f"Skipping {gear_piece.get('slot')} because it had no supported affixes.")
            continue
        if affixes:
            affixes = sorted(affixes, key=lambda affix: (affix.name, affix.type.value))
            item_filter.affix_pool = create_item_affix_pool(affixes=affixes, unique_like=is_unique_like)
            update_mingreateraffixcount(item_filter, config.require_greater_affixes)
        item_filter.min_power = 100
        finished_filters.append(item_filter)
    return Variant(
        affix_filters=finished_filters,
        charm_filters=charm_filters,
        seal_filters=seal_filters,
        aspect_upgrade_filters=aspect_upgrade_filters,
    )
