import dataclasses
import datetime
import json
import logging
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import lxml.html
import seleniumbase
from pydantic import ValidationError

import src.logger
from src.config.loader import IniConfigLoader
from src.config.models import AffixFilterCountModel, AffixFilterModel, ItemFilterModel, ProfileModel
from src.dataloader import Dataloader
from src.gui.importer.common import (
    format_number_as_short_string,
    match_to_enum,
    retry_importer,
    save_as_profile,
)
from src.item.data.affix import Affix
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.text import clean_str, closest_match

LOGGER = logging.getLogger(__name__)

BASE_URL = "diablo.trade/listings/"


@dataclasses.dataclass
class _AnnotatedFilter:
    filter: ItemFilterModel | None = None
    max_price: int | None = None
    min_price: int | None = None


@dataclasses.dataclass
class _Listing:
    affixes: list[Affix] | None = None
    inherents: list[Affix] | None = None
    item_power: int = 0
    item_rarity: ItemRarity | None = None
    item_type: ItemType | None = None
    price: int = 0
    raw_data: dict[str, Any] | None = None


class DiabloTradeException(Exception):
    pass


@retry_importer(inject_webdriver=True, uc=True)
def import_diablo_trade(url: str, max_listings: int, driver: seleniumbase.Driver = None):
    url = url.strip().replace("\n", "")
    if BASE_URL not in url:
        LOGGER.error("Invalid url, please use a diablo.trade filter url")
        return
    LOGGER.info("Start fetching listings")
    all_listings = []
    cursor = 1
    while True:
        api_url = _construct_api_url(listing_url=url, cursor=cursor)
        try:
            driver.default_get(url=api_url)
            source = lxml.html.fromstring(driver.get_page_source())
            data = json.loads(source.text_content().strip())
        except Exception:
            LOGGER.exception("Can't fetch listings, saving current data")
            break
        if not (listings := data["data"]):
            LOGGER.debug("Reached end")
            break
        for listing in listings:
            if not (item_type := match_to_enum(enum_class=ItemType, target_string=listing["itemType"])):
                continue
            if item_type in [None, ItemType.Material]:
                continue
            item_rarity = match_to_enum(enum_class=ItemRarity, target_string=listing["rarity"])
            if item_rarity != ItemRarity.Legendary:
                continue
            listing_obj = _Listing(
                affixes=_create_affixes_from_api_dict(listing["affixes"]),
                inherents=_create_affixes_from_api_dict(listing["implicits"]),
                item_power=listing["itemPower"],
                item_rarity=ItemRarity.Legendary,
                item_type=item_type,
                price=listing["price"],
                raw_data=listing,
            )
            try:
                assert listing_obj.item_type is not None
                assert len(listing["affixes"]) == len(listing_obj.affixes)
                assert len(listing["implicits"]) == len(listing_obj.inherents)
            except AssertionError:
                LOGGER.error(f"If you see this create a bug ticket! {listing=}")
            all_listings.append(listing_obj)
        LOGGER.info(f"Fetched {len(all_listings)} listings")
        if len(all_listings) >= max_listings:
            break
        cursor += 1

    try:
        profile = ProfileModel(name="diablo_trade", Affixes=_create_filters_from_items(items=all_listings))
    except Exception as exc:
        LOGGER.exception(msg := "Failed to validate profile. Dumping data for debugging.")
        with open(
            IniConfigLoader().user_dir / f"diablo_trade_dump_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y_%m_%d_%H_%M_%S')}.json",
            "w",
        ) as f:
            json.dump(all_listings, f, indent=4, sort_keys=True)
        raise DiabloTradeException(msg) from exc

    LOGGER.info(f"Saving profile with {len(profile.Affixes)} filters")
    save_as_profile(
        file_name=f"diablo_trade_{datetime.datetime.now(tz=datetime.UTC).strftime('%Y_%m_%d_%H_%M_%S')}", profile=profile, url=url
    )
    LOGGER.info("Finished")


def _construct_api_url(listing_url: str, cursor: int = 1) -> str:
    parsed_url = urlparse(listing_url)
    query_dict = parse_qs(parsed_url.query)
    query_dict["cursor"] = [str(cursor)]
    new_query_string = urlencode(query_dict, doseq=True)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, "api/items/search", parsed_url.params, new_query_string, parsed_url.fragment))


def _create_affixes_from_api_dict(affixes: list[dict[str, Any]]) -> list[Affix]:
    res = []
    for affix in affixes:
        new_affix = Affix(name=closest_match(clean_str(affix["name"]), Dataloader().affix_dict), value=affix["value"])
        if isinstance(new_affix.value, list):
            if new_affix.value:
                new_affix.value = new_affix.value[0]
            else:
                new_affix.value = 0
        res.append(new_affix)
    if len(affixes) != len(res) or any(x.name is None for x in res):
        LOGGER.error(f"If you see this create a bug ticket! {affixes=}")
    return res


def _create_filters_from_items(items: list[_Listing]) -> list[dict[str, ItemFilterModel]]:
    to_check = items.copy()
    result = []
    for item in items.copy():
        if item not in to_check:
            continue
        to_check.remove(item)
        try:
            annotated_filter = _AnnotatedFilter(
                max_price=item.price,
                min_price=item.price,
                filter=ItemFilterModel(
                    minPower=item.item_power,
                    itemType=[item.item_type],
                    affixPool=[AffixFilterCountModel(count=[AffixFilterModel(name=x.name, value=x.value) for x in item.affixes])],
                ),
            )
        except ValidationError:
            LOGGER.exception(f"Failed validation. Skipping {item=}")
            continue
        to_delete = []
        for to_check_item in [x for x in to_check if x.item_type in annotated_filter.filter.itemType]:
            annotated_filter_affixes = [(x.name, x.value) for x in annotated_filter.filter.affixPool[0].count]
            to_check_item_affixes = [(x.name, x.value) for x in to_check_item.affixes]
            for x in annotated_filter_affixes:
                if not any(a[0] == x[0] for a in to_check_item_affixes):
                    break
            else:
                to_delete.append(to_check_item)
                annotated_filter.min_price = min(annotated_filter.min_price, to_check_item.price)
                annotated_filter.max_price = max(annotated_filter.max_price, to_check_item.price)
                for x in annotated_filter.filter.affixPool[0].count:
                    for y in [a for a in to_check_item.affixes if x.name == a.name]:
                        x.value = min(x.value, y.value)
        for to_delete_item in to_delete:
            to_check.remove(to_delete_item)
        result.append(annotated_filter)
    converted_result = []
    for annotated_filter in result:
        name = f"{annotated_filter.filter.itemType[0].value}_{format_number_as_short_string(annotated_filter.min_price)}"
        if annotated_filter.min_price != annotated_filter.max_price:
            name += f"_{format_number_as_short_string(annotated_filter.max_price)}"
        # if there is a dict with this key name already in the list, append a number to the key name using change_key_of_dict
        suffixed_name = name
        i = 2
        while any(suffixed_name in x for x in converted_result):
            suffixed_name = f"{name}_{i}"
            i += 1
        converted_result.append({suffixed_name: annotated_filter.filter})
    return sorted(converted_result, key=lambda x: next(iter(x)))


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://diablo.trade/listings/items?exactPrice=true&rarity=legendary&sold=true&sort=newest"]
    for x in URLS:
        import_diablo_trade(url=x, max_listings=400)
