import logging
import time
from typing import TYPE_CHECKING

import src.item.descr.read_descr_tts
from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import ItemRefreshType, UnfilteredUniquesType
from src.item.data.affix import AffixType
from src.item.data.item_type import ItemType, is_sigil
from src.item.data.rarity import ItemRarity
from src.item.filter import Filter
from src.scripts.common import (
    ASPECT_UPGRADES_LABEL,
    is_ignored_item,
    is_junk_rarity,
    mark_as_favorite,
    mark_as_junk,
    reset_item_status,
)
from src.utils.custom_mouse import mouse
from src.utils.window import screenshot

if TYPE_CHECKING:
    from src.ui.inventory_base import InventoryBase

LOGGER = logging.getLogger(__name__)


def check_items(inv: InventoryBase, force_refresh: ItemRefreshType, stash_is_open=False):
    occupied, _ = inv.get_item_slots()

    if force_refresh in {ItemRefreshType.force_with_filter, ItemRefreshType.force_without_filter}:
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
        if is_ignored_item(item_descr):
            if (
                not stash_is_open
                and item_descr.item_type == ItemType.TemperManual
                and IniConfigLoader().general.auto_use_temper_manuals
            ):
                mouse.click("right")
            continue

        if not is_junk_rarity(item_descr.rarity):
            num_of_affixed_items_checked += 1
            if item_descr.affixes and all(affix.type == AffixType.greater for affix in item_descr.affixes):
                num_of_items_with_all_ga += 1

        # Check if we want to keep the item
        res = Filter().should_keep(item_descr)
        matched_any_affixes = len(res.matched) > 0 and len(res.matched[0].matched_affixes) > 0
        matched_profile_legendary_aspect = any(
            match.profile.endswith(f".{ASPECT_UPGRADES_LABEL}") for match in res.matched
        )

        # Uniques have special handling. If they have an aspect specifically called out by a profile they are treated
        # like any other item. If not, and there are no non-aspect filters, then they are handled by the handle_uniques
        # property
        if item_descr.rarity == ItemRarity.Unique and item_descr.item_type != ItemType.Tribute:
            if not res.keep:
                mark_as_junk()
            elif res.keep:
                if len(res.matched) == 1 and res.matched[0].profile.lower() == "cosmetics":
                    LOGGER.info("Ignoring unique because it matches no filters and is a cosmetic upgrade.")
                elif res.all_unique_filters_are_aspects and not res.unique_aspect_in_profile:
                    if IniConfigLoader().general.handle_uniques == UnfilteredUniquesType.favorite:
                        mark_as_favorite()
                elif IniConfigLoader().general.mark_as_favorite:
                    mark_as_favorite()
        elif not res.keep:
            if IniConfigLoader().general.do_not_junk_ancestral_legendaries and any(
                affix.type == AffixType.greater for affix in item_descr.affixes
            ):
                LOGGER.info("Skipping marking as junk because it is an ancestral legendary.")
            else:
                mark_as_junk()
        elif (
            res.keep
            and (
                matched_any_affixes
                or matched_profile_legendary_aspect
                or item_descr.rarity == ItemRarity.Mythic
                or is_sigil(item_descr.item_type)
                or item_descr.item_type == ItemType.Tribute
            )
            and IniConfigLoader().general.mark_as_favorite
        ):
            mark_as_favorite()

    LOGGER.debug(f"Time to filter all items in stash/inventory tab: {time.time() - start_checking_items:.2f}s")

    # If more than 80% of the items had all greater affixes that means something is probably wrong
    if num_of_affixed_items_checked > 2 and (num_of_items_with_all_ga / num_of_affixed_items_checked > 0.8):
        LOGGER.warning(
            f"{num_of_items_with_all_ga} out of {num_of_affixed_items_checked} non-junk rarity items checked had all greater affixes. You are either exceptionally lucky or have not enabled Advanced Tooltip Information in Options > Gameplay"
        )
