import json
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import unquote

import jsonpath
import lxml.html
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import src.logger
from src.config.profile_models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    ItemFilterModel,
    ProfileModel,
    SealFilterModel,
)
from src.dataloader import Dataloader
from src.gui.importer.gui_common import (
    add_mythics_to_filters,
    add_to_profiles,
    build_default_profile_file_name,
    create_spellcraft_filter,
    fix_offhand_type,
    fix_weapon_type,
    match_to_enum,
    retry_importer,
    save_as_profile,
    sort_profile_filters,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_mobalytics_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
PROFILE_GUIDE_BASE_URL = f"{BUILD_GUIDE_BASE_URL}profile"
SCRIPT_XPATH = "//script"
BUILD_SCRIPT_ASSIGNMENT = re.compile(r"window\.__PRELOADED_STATE__\s*=\s*")
PAGE_DIAGNOSTIC_MARKERS = (
    "__PRELOADED_STATE__",
    "__NEXT_DATA__",
    "self.__next_f",
    "userGeneratedDocumentBySlug",
    "buildVariants",
    "captcha",
    "cloudflare",
    "access denied",
    "forbidden",
    "just a moment",
)

if TYPE_CHECKING:
    from selenium.webdriver.chromium.webdriver import ChromiumDriver


class MobalyticsError(Exception):
    pass


@retry_importer(inject_webdriver=True, uc=True)
def import_mobalytics(config: ImportConfig, driver: ChromiumDriver = None):
    url = config.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        return
    if PROFILE_GUIDE_BASE_URL in url:
        LOGGER.error("Builds from user profiles are not supported at this time.")
        return
    url = _fix_input_url(url=url)
    LOGGER.info(f"Loading {url}")
    _open_mobalytics_url(driver=driver, url=url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    variant_id = url.split(",")[1].split("#")[0] if "activeVariantId" in url else None
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)
    # The build is shoved in a massive JSON in one of the script tags. We find that json now.
    scripts_elem = raw_html_data.xpath(SCRIPT_XPATH)
    full_script_data_json = None
    for script in scripts_elem:
        full_script_data_json = _extract_mobalytics_preloaded_state(script.text_content())
        if full_script_data_json is not None:
            break

    if not full_script_data_json:
        _log_mobalytics_page_diagnostics(driver=driver, page_source=page_source, script_count=len(scripts_elem))
        LOGGER.error(
            msg
            := "No script containing build data was found. This means Mobalytics has changed how they present data, please submit a bung."
        )
        raise MobalyticsError(msg)

    # Get the JSON block that contains the build and its variants
    build_data = dict(jsonpath.findall("$..userGeneratedDocumentBySlug.data.data", full_script_data_json)[0])
    season_number = _extract_mobalytics_season_number(full_script_data_json)
    build_header = build_data["name"]
    if not build_header:
        LOGGER.error(msg := "No build name found")
        raise MobalyticsError(msg)
    class_name = jsonpath.findall(
        "$..userGeneratedDocumentBySlug.data.tags.data[?@.groupSlug=='class'].name", full_script_data_json
    )[0].lower()
    if not class_name:
        LOGGER.error(msg := "No class name found")
        raise MobalyticsError(msg)
    if variant_id:
        items = jsonpath.findall(f"$..buildVariants.values[?@.id=='{variant_id}'].genericBuilder.slots", build_data)[0]
    else:
        items = jsonpath.findall("$..buildVariants.values[0].genericBuilder.slots", build_data)[0]
        variant_id = jsonpath.findall("$..buildVariants.values[0].id", build_data)[0]

    paragon_data = jsonpath.findall(f"$..buildVariants.values[?@.id=='{variant_id}'].paragon", build_data)[0]

    variant_name = jsonpath.findall(f"$..childrenVariants[?@.id=='{variant_id}'].title", full_script_data_json)
    variant_name = variant_name[0] if variant_name else ""
    build_name = f"{build_header} {variant_name}".strip() if variant_name else build_header

    if not items:
        LOGGER.error(msg := "No items found")
        raise MobalyticsError(msg)
    finished_filters = []
    charm_filters = []
    seal_filters = []
    mythic_names = []
    aspect_upgrade_filters = []
    for item in items:
        item_filter = ItemFilterModel()
        entity_type = jsonpath.findall(".gameEntity.type", item)[0]
        mythic_result = jsonpath.findall(".gameEntity.entity.mythic", item)
        is_mythic = mythic_result[0] if mythic_result else False
        if entity_type not in ["aspects", "uniqueItems", "charms", "seals", "items"]:
            continue
        if not (item_name := str(jsonpath.findall(".gameEntity.entity.title", item)[0])):
            LOGGER.error(msg := "No item name found")
            raise MobalyticsError(msg)
        if not (slot_type := str(jsonpath.findall(".gameSlotSlug", item)[0])):
            LOGGER.error(msg := "No slot type found")
            raise MobalyticsError(msg)

        raw_affixes = jsonpath.findall(".gameEntity.modifiers.gearStats[*]", item)
        raw_inherents = jsonpath.findall(".gameEntity.modifiers.implicitStats[*]", item)
        raw_affixes = [x for x in raw_affixes if x is not None]
        raw_inherents = [x for x in raw_inherents if x is not None]

        is_unique = entity_type == "uniqueItems"
        if is_unique:
            try:
                # We handle mythics at the end
                if is_mythic:
                    mythic_names.append(item_name)
                    continue
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=item_name)]
            except Exception:
                LOGGER.exception(f"Unexpected error adding unique aspect for {item_name}, please report a bug.")

        legendary_aspect = _get_legendary_aspect(item_name)
        if legendary_aspect:
            aspect_upgrade_filters.append(legendary_aspect)

        if not raw_affixes and not raw_inherents:
            LOGGER.warning(f"Skipping {slot_type} because it had no stats provided.")
            continue

        item_type = None
        # Item type is hidden in the inherents. If it's in there, then we assume there are no further inherents
        is_weapon = "weapon" in slot_type
        for inherent in raw_inherents:
            potential_item_type = " ".join(inherent["id"].split("-")[:2]).lower()
            if is_weapon and (x := fix_weapon_type(input_str=potential_item_type)) is not None:
                item_type = x
                break
            if (
                "offhand" in slot_type
                and (x := fix_offhand_type(input_str=inherent["id"].replace("-", " "), class_str=class_name))
                is not None
            ):
                item_type = x
                break
        if item_type:
            raw_inherents.clear()

        # Druid and sorc have a default offhand item type that we may have missed if there were no inherents
        if not item_type and "offhand" in slot_type:
            item_type = fix_offhand_type("", class_name)

        item_type = (
            match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot_type))
            if item_type is None
            else item_type
        )
        if item_type is None:
            if is_weapon:
                LOGGER.warning(
                    f"Couldn't find an item_type for weapon slot {slot_type}, defaulting to all weapon types instead."
                )
                item_filter.item_type = WEAPON_TYPES
            else:
                item_filter.item_type = []
                LOGGER.warning(f"Couldn't match item_type: {slot_type}. Please edit manually")
        else:
            item_filter.item_type = [item_type]

        affixes = _convert_raw_to_affixes(raw_affixes, config.import_greater_affixes)
        inherents = _convert_raw_to_affixes(raw_inherents)

        if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
            if not affixes:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes.")
                continue
            spellcraft_filters = charm_filters if item_type == ItemType.Charm else seal_filters
            filter_name = _unique_filter_name(item_type.name, spellcraft_filters)
            spellcraft_model = CharmFilterModel if item_type == ItemType.Charm else SealFilterModel
            spellcraft_filters.append({
                filter_name: create_spellcraft_filter(
                    affixes=affixes,
                    rarity=None,
                    require_gas=config.require_greater_affixes,
                    model_type=spellcraft_model,
                )
            })
            continue

        if not is_mythic:
            item_filter.affix_pool = [
                AffixFilterCountModel(
                    count=[AffixFilterModel(name=x.name, want_greater=x.type == AffixType.greater) for x in affixes],
                    min_count=1 if is_unique else 3,
                )
            ]
            update_mingreateraffixcount(item_filter, config.require_greater_affixes)
        item_filter.min_power = 100
        if inherents and not is_mythic:
            item_filter.inherent_pool = [
                AffixFilterCountModel(count=[AffixFilterModel(name=x.name) for x in inherents])
            ]
        filter_name_template = item_filter.item_type[0].name if item_type else slot_type.replace(" ", "")
        filter_name = _unique_filter_name(filter_name_template, finished_filters)
        finished_filters.append({filter_name: item_filter})

    # Place all mythics in a single filter
    add_mythics_to_filters(mythic_names, finished_filters)
    profile = ProfileModel(
        name="imported profile",
        Affixes=sort_profile_filters(finished_filters),
        Charms=sort_profile_filters(charm_filters),
        Seals=sort_profile_filters(seal_filters),
    )
    if config.import_aspect_upgrades and aspect_upgrade_filters:
        profile.aspect_upgrades = aspect_upgrade_filters

    file_name = config.custom_file_name or build_default_profile_file_name(
        source_name="mobalytics",
        class_name=class_name,
        season_number=season_number,
        build_header=build_header,
        variant_name=variant_name,
    )
    # Optionally embed Paragon data into the profile model before saving
    if config.export_paragon:
        steps = extract_mobalytics_paragon_steps(paragon_data if isinstance(paragon_data, dict) else {})
        if steps:
            profile.paragon = build_paragon_profile_payload(
                build_name=build_name, source_url=url, paragon_boards_list=steps
            )
        else:
            LOGGER.warning("Paragon export enabled, but no paragon data was found for this Mobalytics variant.")

    corrected_file_name = save_as_profile(file_name=file_name, profile=profile, url=url)

    if config.add_to_profiles:
        add_to_profiles(corrected_file_name)

    LOGGER.info("Finished")


def _corrections(input_str: str) -> str:
    match input_str.lower():
        case "max life":
            return "maximum life"
    return input_str


def _fix_input_url(url: str) -> str:
    return unquote(url)


def _open_mobalytics_url(driver: ChromiumDriver, url: str) -> None:
    if hasattr(driver, "uc_open_with_reconnect"):
        driver.uc_open_with_reconnect(url, reconnect_time=4)
        return
    driver.get(url)


def _extract_mobalytics_preloaded_state(script_text: str) -> dict | None:
    match = BUILD_SCRIPT_ASSIGNMENT.search(script_text)
    if match is None:
        return None
    script_json = script_text[match.end() :].strip()
    try:
        data, _ = json.JSONDecoder().raw_decode(script_json)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _log_mobalytics_page_diagnostics(driver: ChromiumDriver, page_source: str, script_count: int) -> None:
    page_source_casefold = page_source.casefold()
    matched_markers = [marker for marker in PAGE_DIAGNOSTIC_MARKERS if marker.casefold() in page_source_casefold]
    LOGGER.debug(
        "Mobalytics page diagnostics: current_url=%r title=%r page_source_length=%s script_count=%s markers=%s",
        _read_mobalytics_driver_value(driver, "current_url"),
        _read_mobalytics_driver_value(driver, "title"),
        len(page_source),
        script_count,
        ", ".join(matched_markers) or "none",
    )


def _read_mobalytics_driver_value(driver: ChromiumDriver, value_name: str) -> str:
    try:
        value = getattr(driver, value_name)
    except WebDriverException as exc:
        return f"<unavailable: {exc.__class__.__name__}>"
    return str(value)


def _extract_mobalytics_season_number(full_script_data_json: dict) -> str:
    tag_names = jsonpath.findall("$..userGeneratedDocumentBySlug.data.tags.data[*].name", full_script_data_json)
    for tag_name in tag_names:
        if season_match := re.search(r"\bSeason\s+(\d+)\b", str(tag_name), flags=re.IGNORECASE):
            season_number = season_match.group(1)
            break
    else:
        season_number = ""
    return season_number


def _get_legendary_aspect(name: str) -> str:
    if "aspect" in name.lower():
        aspect_name = correct_name(name.lower().replace("aspect", "").strip())

        if aspect_name not in Dataloader().aspect_list:
            LOGGER.warning(
                f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
            )
        else:
            return aspect_name
    return ""


def _convert_raw_to_affixes(raw_stats: list[dict], import_greater_affixes=False) -> list[Affix]:
    result = []
    for stat in raw_stats:
        if stat:
            affix_obj = Affix(
                name=closest_match(clean_str(_corrections(input_str=stat["id"])), Dataloader().affix_dict)
            )
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {stat=}")
                continue
            if import_greater_affixes and stat.get("isGreater", False):
                affix_obj.type = AffixType.greater
            result.append(affix_obj)
    return result


def _unique_filter_name(filter_name_template: str, filters: list[dict]) -> str:
    filter_name = filter_name_template
    i = 2
    while any(filter_name == next(iter(existing_filter)) for existing_filter in filters):
        filter_name = f"{filter_name_template}{i}"
        i += 1
    return filter_name


if __name__ == "__main__":
    src.logger.setup()

    from selenium import webdriver

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("log-level=3")
    driver = webdriver.Chrome(options=options)

    URLS = [
        # # No frills and no uniques
        # "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb",
        # # Is a variant of the one above
        # "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb?ws-ngf5-1=activeVariantId%2C7a9c6d51-18e9-4090-a804-7b73ff00879d",
        # # This one has no variants at all, just to make sure that works too
        # "https://mobalytics.gg/diablo-4/profile/screamheart/builds/15x-thrash-out-of-date",
        # # This one has an item type for the weapon
        # "https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
        # # This has a necro offhand
        # "https://mobalytics.gg/diablo-4/builds/necromancer-kripp-golem-summoner",
        # # This has two rogue offhand weapons
        # "https://mobalytics.gg/diablo-4/builds/rogue-efficientrogue-dance-of-knives?ws-ngf5-1=activeVariantId%2Ca2977139-f3e2-4b13-aa64-82ba69972528",
        # Season 13 testing
        "https://mobalytics.gg/diablo-4/builds/barbarian-ancients-leap-endgame"
    ]
    for X in URLS:
        config = ImportConfig(
            url=X,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            export_paragon=True,
            custom_file_name=None,
        )
        import_mobalytics(config, driver)
