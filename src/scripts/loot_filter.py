import logging
import time

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import HandleRaresType, ItemRefreshType, UnfilteredUniquesType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr import read_descr
from src.item.filter import Filter
from src.item.find_descr import find_descr
from src.scripts.common import mark_as_favorite, mark_as_junk, reset_item_status
from src.ui.inventory_base import InventoryBase
from src.utils.image_operations import compare_histograms
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
    start_time = None
    img = None
    for item in occupied:
        if item.is_junk or item.is_fav:
            continue
        if start_time is not None:
            LOGGER.debug(f"Runtime (FullItemCheck): {time.time() - start_time:.2f}s")
            LOGGER.debug("----")
        # Find item descr
        start_time = time.time()
        found = False
        while not found:
            if time.time() - start_time > 6:
                LOGGER.error("Could not detect item descr. Timeout reached. Continue")
                if img is not None:
                    screenshot("failed_descr_detection", img=img)
                break
            inv.hover_item(item)
            time.sleep(0.2)
            img = Cam().grab()
            start_detect = time.time()
            found, rarity, cropped_descr, _ = find_descr(img, item.center)
            if found:
                # To avoid getting an image that is taken while the fade-in animation of the item is showing
                found_check, _, cropped_descr_check, _ = find_descr(Cam().grab(), item.center)
                if found_check:
                    score = compare_histograms(cropped_descr, cropped_descr_check)
                    if score < 0.99:
                        found = False
                        continue
            LOGGER.debug(f"  Runtime (DetectItem): {time.time() - start_detect:.2f}s")
        if not found:
            continue

        start_time_read = time.time()
        # Detect contents of item descr
        item_descr = read_descr(rarity, cropped_descr, False)
        if item_descr is None:
            LOGGER.info("Retry item detection")
            time.sleep(0.2)
            found, rarity, cropped_descr, _ = find_descr(Cam().grab(), item.center)
            if found:
                item_descr = read_descr(rarity, cropped_descr)
            if item_descr is None:
                continue
        LOGGER.debug(f"  Runtime (ReadItem): {time.time() - start_time_read:.2f}s")

        # Hardcoded filters
        if rarity == ItemRarity.Common and item_descr.item_type == ItemType.Material:
            LOGGER.info("Matched: Material")
            continue
        if rarity == ItemRarity.Legendary and item_descr.item_type == ItemType.Material:
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
        if rarity in [ItemRarity.Magic, ItemRarity.Common] and item_descr.item_type != ItemType.Sigil:
            mark_as_junk()
            continue
        if rarity == ItemRarity.Rare and IniConfigLoader().general.handle_rares == HandleRaresType.ignore:
            LOGGER.info("Matched: Rare, ignore Item")
            continue
        if rarity == ItemRarity.Rare and IniConfigLoader().general.handle_rares == HandleRaresType.junk:
            mark_as_junk()
            continue

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
                mark_as_junk()
            elif (
                res.keep
                and (matched_any_affixes or item_descr.rarity == ItemRarity.Mythic or item_descr.item_type == ItemType.Sigil)
                and IniConfigLoader().general.mark_as_favorite
            ):
                mark_as_favorite()
