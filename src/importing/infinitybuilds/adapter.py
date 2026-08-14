import logging
from typing import TYPE_CHECKING

import lxml.html
from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.game_data import GameCatalog, ItemRarity, ItemType
from src.importing.contracts import ImportRequest, ImportResult, ImportSourceError, VariantMetadata
from src.importing.filters import (
    create_item_affix_pool,
    create_seal_charm_filter,
    is_unique_like_rarity,
    match_to_enum,
    update_mingreateraffixcount,
)
from src.importing.infinitybuilds._talisman import _charm_set_name
from src.importing.infinitybuilds.extraction import (
    _canonical_catalog_id,
    _convert_raw_to_affixes,
    _extract_build_data,
    _extract_build_title,
    _normalize_aspect_name,
    _resolve_gear_data,
)
from src.importing.infinitybuilds.paragon import (
    InfinityBuildsParagonCatalog,
    extract_infinitybuilds_paragon_steps,
    fetch_infinitybuilds_paragon_catalog,
)
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.importing.web import retry_importer
from src.profiles import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel

if TYPE_CHECKING:
    from collections.abc import Sequence

    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing.infinitybuilds.models import BuildData, _GearPiece, _ResolvedGearData
LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://infinitybuilds.gg/"
SCRIPT_XPATH = "//script"
ASPECT_UPGRADE_RARITIES = {"legendary"}


class InfinityBuildsError(ImportSourceError):
    pass


def _validated_url(request: ImportRequest, driver: WebDriver | None) -> tuple[str, WebDriver] | None:
    if driver is None:
        msg = "A Selenium WebDriver is required for InfinityBuilds imports"
        raise RuntimeError(msg)
    url = request.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use an infinitybuilds.gg build link")
        return None
    return url, driver


def _load_build_page(url: str, driver: WebDriver) -> tuple[etree._Element, BuildData]:
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    wait.until(lambda d: "classId" in d.page_source and "variants" in d.page_source)
    raw_html_data = lxml.html.fromstring(driver.page_source, parser=lxml.html.HTMLParser())
    if (build_data := _extract_build_data(raw_html_data)) is None:
        message = "No build data found in the InfinityBuilds page"
        raise InfinityBuildsError(message)
    return raw_html_data, build_data


@retry_importer(inject_webdriver=True)
def fetch_variants_infinitybuilds(request: ImportRequest, driver: WebDriver | None = None) -> list[VariantMetadata]:
    validated = _validated_url(request, driver)
    if validated is None:
        return []
    url, driver = validated
    LOGGER.info(f"Loading {url} for variants")
    try:
        raw_html_data, build_data = _load_build_page(url, driver)
    except InfinityBuildsError:
        return []
    variants_data = build_data.get("variants") or []
    variants = []
    for variant in variants_data:
        if variant.get("gear"):
            variant_id = str(variant.get("id") or len(variants))
            variants.append(VariantMetadata(id=variant_id, name=variant.get("name") or f"Variant {variant_id}"))
    return variants


def import_infinitybuilds(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    return _import_infinitybuilds(request, driver)


@retry_importer(inject_webdriver=True)
def _import_infinitybuilds(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    validated = _validated_url(request, driver)
    if validated is None:
        return None
    url, driver = validated
    LOGGER.info(f"Loading {url}")
    # The build data is streamed in via React Server Components after initial hydration; the
    # shared loader waits for the hydrated payload before parsing it.
    raw_html_data, build_data = _load_build_page(url, driver)
    build_header = _extract_build_title(raw_html_data)
    class_name = build_data.get("classId", "")
    if not class_name:
        LOGGER.error(msg := "No class name found")
        raise InfinityBuildsError(msg)
    variants = build_data.get("variants") or []
    variants = [v for v in variants if v.get("gear")]
    if not variants:
        LOGGER.error(msg := "No gear found for this build")
        raise InfinityBuildsError(msg)
    if request.options.multi_build and request.variant_selection is not None:
        # Filter variants by selected IDs if provided (fallback to index string if ID missing)
        variants = [
            variant
            for index, variant in enumerate(variants)
            if str(variant.get("id") or index) in request.variant_selection
        ]
    # Resolve all variants' gear in a single API call to avoid redundant round trips.
    variant_gear = [variant["gear"] + variant.get("talisman", []) for variant in variants]
    resolved = _resolve_gear_data(class_name, [piece for gear in variant_gear for piece in gear])
    paragon_catalog: InfinityBuildsParagonCatalog | None = None
    if request.options.export_paragon:
        try:
            paragon_catalog = fetch_infinitybuilds_paragon_catalog()
        except TypeError, ValueError:
            LOGGER.warning(
                "Could not fetch InfinityBuilds paragon catalog data, skipping paragon export.", exc_info=True
            )
    extracted_variants = []
    for variant, gear in zip(variants, variant_gear, strict=True):
        extracted_variant = _build_variant_for_gear(gear=gear, resolved=resolved, request=request)
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
        request=request,
    )


def _build_variant_for_gear(gear: Sequence[_GearPiece], resolved: _ResolvedGearData, request: ImportRequest) -> Variant:
    finished_filters: list[ItemFilterModel] = []
    charm_filters: list[CharmFilterModel] = []
    seal_filters: list[SealFilterModel] = []
    aspect_upgrade_filters: list[str] = []
    for raw_gear_piece in gear:
        gear_piece = raw_gear_piece
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
        if aspect_name and rarity in ASPECT_UPGRADE_RARITIES and request.options.import_aspect_upgrades:
            normalized_aspect_name = _normalize_aspect_name(aspect_name)
            if normalized_aspect_name in GameCatalog().aspect_list:
                aspect_upgrade_filters.append(normalized_aspect_name)
            else:
                LOGGER.warning(
                    f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
                )
        affixes = _convert_raw_to_affixes(
            gear_piece.get("affixes") or [],
            resolved.affixes,
            request.options.import_greater_affixes,
            item_type=item_type,
        )
        if item_type == ItemType.Charm:
            unique_name = item_name if is_unique_like else None
            set_name = _charm_set_name(item_name)
            charm_rarity = match_to_enum(ItemRarity, "common" if rarity == "normal" else rarity)
            if not affixes and not unique_name and not set_name and charm_rarity is None:
                LOGGER.warning(
                    f"Skipping {item_name} because it had no supported affixes, unique aspect, set, or rarity."
                )
                continue
            charm_filter = create_seal_charm_filter(
                affixes=affixes,
                require_gas=request.options.require_greater_affixes,
                model_type=CharmFilterModel,
                unique_name=unique_name,
                set_name=set_name,
            )
            charm_filter.rarities = [charm_rarity] if charm_rarity else []
            charm_filters.append(charm_filter)
            continue
        if item_type == ItemType.HoradricSeal:
            unique_name = item_name if is_unique_like else None
            seal_rarity = match_to_enum(ItemRarity, rarity)
            if not affixes and not unique_name and seal_rarity is None:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes, unique aspect, or rarity.")
                continue
            seal_filter = create_seal_charm_filter(
                affixes=affixes,
                require_gas=request.options.require_greater_affixes,
                model_type=SealFilterModel,
                unique_name=unique_name,
            )
            seal_filter.rarities = [seal_rarity] if seal_rarity else []
            seal_filters.append(seal_filter)
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
            update_mingreateraffixcount(item_filter, request.options.require_greater_affixes)
        item_filter.min_power = 100
        finished_filters.append(item_filter)
    return Variant(
        affix_filters=finished_filters,
        charm_filters=charm_filters,
        seal_filters=seal_filters,
        aspect_upgrade_filters=aspect_upgrade_filters,
    )
