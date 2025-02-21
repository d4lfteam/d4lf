import logging
import time

import src.item.descr.read_descr_tts
from item.data.affix import AffixType
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ItemRefreshType, UnfilteredUniquesType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.filter import Filter
from src.scripts.common import mark_as_favorite, mark_as_junk, reset_item_status
from src.ui.inventory_base import InventoryBase
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)


def check_items(inv: InventoryBase, force_refresh: ItemRefreshType):
    occupied, _ = inv.get_item_slots()

    if force_refresh == ItemRefreshType.force_with_filter or force_refresh == ItemRefreshType.force_without_filter:
        reset_item_status(occupied, inv)
        occupied, _ = inv.get_item_slots()

    if force_refresh == ItemRefreshType.force_without_filter:
        return

    num_fav = sum(1 for slot in occupied if slot.is_fav)
    num_junk = sum(1 for slot in occupied if slot.is_junk)
    LOGGER.info(f"Items: {len(occupied)} (favorite: {num_fav}, junk: {num_junk}) in {inv.menu_name}")
    # These are used to check if there's any signs that the user does not have Advanced Tooltip Comparison on
    num_of_items_with_all_ga = 0
    num_of_affixed_items_checked = 0
    start_checking_items = time.time()
    for item in occupied:
        if item.is_junk or item.is_fav:
            continue
        inv.hover_item_with_delay(item)
        time.sleep(0.1)
        img = Cam().grab()
        item_descr = None
        retry_count = 0

        while item_descr is None and retry_count != 2:
            try:
                item_descr = src.item.descr.read_descr_tts.read_descr()
                LOGGER.debug(f"Attempt {retry_count} to parse item based on TTS: {item_descr}")
                retry_count += 1
            except Exception:
                screenshot("tts_error", img=img)
                LOGGER.exception(f"Error in TTS read_descr. {src.tts.LAST_ITEM=}")

        if item_descr is None:
            continue

        # Hardcoded filters
        if item_descr.rarity == ItemRarity.Common and item_descr.item_type == ItemType.Material:
            LOGGER.info("Matched: Material")
            continue
        if item_descr.rarity == ItemRarity.Legendary and item_descr.item_type == ItemType.Material:
            LOGGER.info("Matched: Extracted Aspect")
            continue
        if item_descr.item_type == ItemType.Elixir:
            LOGGER.info("Matched: Elixir")
            continue
        if item_descr.item_type == ItemType.Incense:
            LOGGER.info("Matched: Incense")
            continue
        if item_descr.item_type == ItemType.TemperManual:
            LOGGER.info("Matched: Temper Manual")
            continue
        if item_descr.item_type == ItemType.Cache:
            LOGGER.info("Matched: Cache")
            continue
        if item_descr.rarity in [ItemRarity.Rare, ItemRarity.Magic, ItemRarity.Common] and item_descr.item_type != ItemType.Sigil:
            mark_as_junk()
            continue

        num_of_affixed_items_checked += 1
        if all(affix.type.value == AffixType.greater.value for affix in item_descr.affixes):
            num_of_items_with_all_ga += 1

        # Check if we want to keep the item
        start_filter = time.time()
        res = Filter().should_keep(item_descr)
        matched_any_affixes = len(res.matched) > 0 and len(res.matched[0].matched_affixes) > 0
        LOGGER.debug(f"  Runtime (Filter): {time.time() - start_filter:.2f}s")

        # Uniques have special handling. If they have an aspect specifically called out by a profile they are treated
        # like any other item. If not, and there are no non-aspect filters, then they are handled by the handle_uniques
        # property
        if item_descr.rarity == ItemRarity.Unique:
            if not res.keep:
                mark_as_junk()
            elif res.keep:
                if res.all_unique_filters_are_aspects and not res.unique_aspect_in_profile:
                    if IniConfigLoader().general.handle_uniques == UnfilteredUniquesType.favorite:
                        mark_as_favorite()
                elif IniConfigLoader().general.mark_as_favorite:
                    mark_as_favorite()
        else:
            if not res.keep:
                # Specific functionality for Season 7 to help complete challenge to salvage ancestral legendaries
                # The .value shouldn't be needed here but for some reason the direct comparison never worked
                is_greater = any(affix.type.value == AffixType.greater.value for affix in item_descr.affixes)
                if is_greater and IniConfigLoader().general.s7_do_not_junk_ancestral_legendaries:
                    LOGGER.info("Skipping marking as junk because it is an ancestral legendary.")
                else:
                    mark_as_junk()
            elif (
                res.keep
                and (matched_any_affixes or item_descr.rarity == ItemRarity.Mythic or item_descr.item_type == ItemType.Sigil)
                and IniConfigLoader().general.mark_as_favorite
            ):
                mark_as_favorite()

    LOGGER.debug(f"  Time to filter all items in stash/inventory tab: {time.time() - start_checking_items:.2f}s")

    # If more than 80% of the items had all greater affixes that means something is probably wrong
    if num_of_affixed_items_checked > 1 and (num_of_items_with_all_ga / num_of_affixed_items_checked > 0.8):
        LOGGER.warning(
            f"{num_of_items_with_all_ga} out of {num_of_affixed_items_checked} items checked had all greater affixes. You are either exceptionally lucky or have not enabled Advanced Tooltip Information in Options > Gameplay"
        )
