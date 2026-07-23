import logging
import re
from typing import TYPE_CHECKING

from src.importing.d4builds.constants import (
    BUILD_OVERVIEW_XPATH,
    GA_XPATH,
    ITEM_SLOT_XPATH,
    ITEM_STATS_XPATH,
    SANCTIFIED_ICON_XPATH,
    TEMPERING_ICON_XPATH,
)
from src.importing.d4builds.extraction import (
    _corrections,
    _extract_d4builds_seal_charm_filters,
    _get_weapon_paperdoll_icons,
    _get_weapon_type_from_paperdoll_tooltip,
)
from src.importing.d4builds.metadata import D4BuildsError, _get_affix_name, _get_item_slots, _get_legendary_aspects
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
from src.importing.pipeline import Variant
from src.item import WEAPON_TYPES, Affix, AffixType, ItemType
from src.perception import clean_str, closest_match
from src.profiles import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, ItemFilterModel

if TYPE_CHECKING:
    from lxml import html
    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing.contracts import ImportRequest


LOGGER = logging.getLogger(__name__)


def extract_variant(
    *,
    data: html.HtmlElement,
    driver: WebDriver,
    request: ImportRequest,
    class_name: str,
    build_header: str,
    variant_name: str,
) -> Variant:
    if not (items := data.xpath(BUILD_OVERVIEW_XPATH)):
        message = "No items found"
        LOGGER.error(message)
        raise D4BuildsError(message)

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
                if any(substring in affix_name.lower() for substring in ["focus", "offhand", "shield", "totem"]):
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

    return Variant(
        name=variant_name,
        affix_filters=finished_filters,
        affix_filter_name_hints=finished_filter_name_hints,
        charm_filters=charm_filters,
        seal_filters=seal_filters,
        aspect_upgrade_filters=aspect_upgrade_filters,
        paragon_steps=extract_d4builds_paragon_steps(driver, class_name=class_name),
        paragon_build_name=build_header or class_name,
    )
