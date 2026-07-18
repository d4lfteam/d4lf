import logging
import time
from typing import TYPE_CHECKING

import src.perception
from src import automation
from src.item import ASPECT_UPGRADES_LABEL, AffixType, Filter, ItemRarity, ItemType, is_sigil
from src.perception import capture, screenshot
from src.settings import ItemRefreshType, UnfilteredUniquesType, get_settings

from ._colors import drop_item_from_inventory, is_ignored_item, mark_as_favorite, mark_as_junk, reset_item_status

if TYPE_CHECKING:
    from src.automation import Inventory

LOGGER = logging.getLogger(__name__)


def check_items(
    inv: Inventory, force_refresh: ItemRefreshType, stash_is_open: bool = False, no_match_action: str = "junk"
):
    occupied, _ = inv.get_item_slots()

    def _handle_no_match() -> None:
        if no_match_action == "drop" and not stash_is_open:
            drop_item_from_inventory()
        else:
            mark_as_junk()

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
        img = capture()
        item_descr = None
        retry_count = 0

        while item_descr is None and retry_count != 2:
            try:
                item_descr = src.perception.read_latest_item()
                LOGGER.debug(f"Attempt {retry_count} to parse item based on TTS: {item_descr}")
                retry_count += 1
            except Exception:
                screenshot("tts_error", img=img)
                LOGGER.exception(f"Error in TTS read_descr. {src.perception.latest_item_lines()=}")

        if item_descr is None:
            continue

        # Hardcoded filters
        if is_ignored_item(item_descr):
            if (
                not stash_is_open
                and item_descr.item_type == ItemType.TemperManual
                and get_settings().general.auto_use_temper_manuals
            ):
                automation.click_pointer("right")
            continue

        num_of_affixed_items_checked += 1
        if item_descr.affixes and all(affix.type == AffixType.greater for affix in item_descr.affixes):
            num_of_items_with_all_ga += 1

        # Check if we want to keep the item
        res = Filter().should_keep(item_descr)
        matched_any_affixes = len(res.matched) > 0 and len(res.matched[0].matched_affixes) > 0
        matched_profile_legendary_aspect = any(
            match.profile.endswith(f".{ASPECT_UPGRADES_LABEL}") for match in res.matched
        )

        # Uniques have special handling. They might be a keep but should actually be ignored
        if item_descr.rarity == ItemRarity.Unique and item_descr.item_type != ItemType.Tribute:
            if not res.keep:
                _handle_no_match()
            elif res.keep:
                if len(res.matched) == 1 and res.matched[0].profile.lower() == "cosmetics":
                    LOGGER.info("Ignoring unique because it matches no filters and is a cosmetic upgrade.")
                elif any(match.aspect_match for match in res.matched) and get_settings().general.mark_as_favorite:
                    # This means it was a legitimate match, not an ignore
                    mark_as_favorite()
                elif get_settings().general.handle_uniques == UnfilteredUniquesType.favorite:
                    mark_as_favorite()
        elif not res.keep:
            if get_settings().general.do_not_junk_ancestral_legendaries and item_descr.is_ancestral:
                LOGGER.info("Skipping marking as junk because it is an ancestral legendary.")
            else:
                _handle_no_match()
        elif (
            res.keep
            and (
                matched_any_affixes
                or matched_profile_legendary_aspect
                or item_descr.rarity == ItemRarity.Mythic
                or is_sigil(item_descr.item_type)
                or item_descr.item_type == ItemType.Tribute
            )
            and get_settings().general.mark_as_favorite
        ):
            mark_as_favorite()

    LOGGER.debug(f"Time to filter all items in stash/inventory tab: {time.time() - start_checking_items:.2f}s")

    # If more than 80% of the items had all greater affixes that means something is probably wrong
    if num_of_affixed_items_checked > 2 and (num_of_items_with_all_ga / num_of_affixed_items_checked > 0.8):
        LOGGER.warning(
            f"{num_of_items_with_all_ga} out of {num_of_affixed_items_checked} non-junk rarity items checked had all greater affixes. You are either exceptionally lucky or have not enabled Advanced Tooltip Information in Options > Gameplay"
        )
