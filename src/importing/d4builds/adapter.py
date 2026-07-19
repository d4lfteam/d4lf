import logging
import re
import time
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.importing.d4builds.constants import (
    BASE_URL,
    BUILD_OVERVIEW_XPATH,
    GA_XPATH,
    ITEM_SLOT_XPATH,
    ITEM_STATS_XPATH,
    PAPERDOLL_XPATH,
    SANCTIFIED_ICON_XPATH,
    TEMPERING_ICON_XPATH,
)
from src.importing.d4builds.extraction import (
    _corrections,
    _extract_d4builds_seal_charm_filters,
    _get_weapon_paperdoll_icons,
    _get_weapon_type_from_paperdoll_tooltip,
)
from src.importing.d4builds.metadata import (
    D4BuildsError,
    _extract_build_metadata,
    _get_affix_name,
    _get_item_slots,
    _get_legendary_aspects,
)
from src.importing.d4builds.paragon import extract_d4builds_paragon_steps
from src.importing.filters import (
    affix_dict_for_item_type,
    create_item_affix_pool,
    fix_offhand_type,
    fix_weapon_type,
    is_unique_like_rarity,
    match_to_enum,
    update_mingreateraffixcount,
    weapon_slot_name_hint,
)
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.importing.web import retry_importer
from src.item import WEAPON_TYPES, Affix, AffixType, ItemType
from src.perception import clean_str, closest_match
from src.profiles import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, ItemFilterModel

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing.contracts import ImportRequest, ImportResult


LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True


@retry_importer(inject_webdriver=True)
def import_d4builds(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    if driver is None:
        msg = "A Selenium WebDriver is required for D4Builds imports"
        raise RuntimeError(msg)
    url = request.url
    if BASE_URL not in url:
        LOGGER.error("Invalid url, please use a d4builds url")
        return None
    LOGGER.info(f"Loading {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
    wait.until(ec.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
    time.sleep(
        5
    )  # super hacky but I didn't find anything else. The page is not fully loaded when the above wait is done
    data = lxml.html.fromstring(driver.page_source)
    class_name, build_header, season_number, variant_name = _extract_build_metadata(data=data)
    if not (items := data.xpath(BUILD_OVERVIEW_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsError(msg)
    slot_to_unique_name_map = _get_item_slots(data=data)
    weapon_paperdoll_icons = _get_weapon_paperdoll_icons(driver=driver)
    finished_filters: list[ItemFilterModel] = []
    finished_filter_name_hints: list[str | None] = []
    charm_filters, seal_filters = _extract_d4builds_seal_charm_filters(driver=driver, request=request)
    aspect_upgrade_filters = _get_legendary_aspects(data=data)
    for item in items[0]:
        item_filter = ItemFilterModel()
        if not (slot := item.xpath(ITEM_SLOT_XPATH)[1].tail):
            LOGGER.error("No item_type found")
            continue
        if slot not in slot_to_unique_name_map:
            LOGGER.warning(f"Empty slots are not supported. Skipping: {slot}")
            continue

        stats = item.xpath(ITEM_STATS_XPATH)
        if not stats:
            LOGGER.error(f"No stats found for {slot=}")
            continue

        item_type = None
        rarity = None
        affixes = []
        inherents = []

        unique_item = slot_to_unique_name_map[slot]
        if unique_item is not None:
            unique_name, rarity = unique_item
            try:
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=unique_name)]
            except Exception:
                LOGGER.exception(
                    f"Unexpected error adding unique aspect for {unique_name}, please report a bug and include a link to the build you were trying to import."
                )
        is_unique_like = is_unique_like_rarity(rarity)

        is_weapon = "weapon" in slot.lower()
        affix_dict = affix_dict_for_item_type(item_type=item_type)
        for stat in stats:
            if stat.xpath(TEMPERING_ICON_XPATH) or stat.xpath(SANCTIFIED_ICON_XPATH):
                continue
            if "filled" not in stat.xpath("../..")[0].attrib["class"]:
                continue
            affix_name = _get_affix_name(stat)
            if not affix_name:
                LOGGER.warning(f"Slot {slot} is missing an affix, skipping import of that affix.")
                continue
            if is_weapon and (x := fix_weapon_type(input_str=affix_name)) is not None:
                item_type = x
                continue
            if (
                "offhand" in slot.lower()
                and (x := fix_offhand_type(input_str=affix_name, class_str=class_name)) is not None
            ):
                item_type = x
                if any(
                    substring in affix_name.lower() for substring in ["focus", "offhand", "shield", "totem"]
                ):  # special line indicating the item type
                    continue
            affix_obj = Affix(name=closest_match(clean_str(_corrections(input_str=affix_name)), affix_dict))
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {affix_name=}")
                continue
            if request.options.import_greater_affixes and stat.xpath("../../../..")[0].xpath(GA_XPATH):
                affix_obj.type = AffixType.greater
            affixes.append(affix_obj)

        item_type = (
            match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot.replace(" ", "")))
            if item_type is None
            else item_type
        )

        if not affixes and not item_filter.unique_aspect:
            continue

        if item_type is None and is_weapon and (icon := weapon_paperdoll_icons.get(slot)) is not None:
            item_type = _get_weapon_type_from_paperdoll_tooltip(driver=driver, icon=icon)

        if item_type is None:
            if is_weapon:
                LOGGER.warning(
                    f"Couldn't find an item_type for weapon slot {slot}, defaulting to all weapon types instead."
                )
                item_filter.item_type = WEAPON_TYPES
            else:
                item_filter.item_type = []
                LOGGER.warning(f"Couldn't match item_type: {slot}. Please edit manually")
        else:
            item_filter.item_type = [item_type]

        if affixes:
            item_filter.affix_pool = create_item_affix_pool(affixes=affixes, unique_like=is_unique_like)
            update_mingreateraffixcount(item_filter, request.options.require_greater_affixes)
            if inherents:
                item_filter.inherent_pool = [
                    AffixFilterCountModel(count=[AffixFilterModel(name=x.name) for x in inherents])
                ]
        item_filter.min_power = 100
        finished_filters.append(item_filter)
        finished_filter_name_hints.append(weapon_slot_name_hint(item_filter, slot))
    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="d4builds",
                class_name=class_name,
                build_header=build_header,
                season_number=season_number,
                variants=[
                    Variant(
                        name=variant_name,
                        affix_filters=finished_filters,
                        affix_filter_name_hints=finished_filter_name_hints,
                        charm_filters=charm_filters,
                        seal_filters=seal_filters,
                        aspect_upgrade_filters=aspect_upgrade_filters,
                        paragon_steps=extract_d4builds_paragon_steps(driver, class_name=class_name),
                        paragon_build_name=build_header or class_name,
                    )
                ],
            ),
        ),
        request=request,
    )
