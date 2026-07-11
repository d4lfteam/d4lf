import json
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import unquote

import jsonpath
import lxml.html
import rapidfuzz
from selenium.common.exceptions import NoSuchElementException, WebDriverException
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
    SealFilterModel,
)
from src.dataloader import Dataloader
from src.gui.importer.gui_common import (
    affix_dict_for_item_type,
    create_item_affix_pool,
    create_seal_charm_filter,
    fix_offhand_type,
    fix_weapon_type,
    hover_and_get_tooltip_html,
    match_to_enum,
    retry_importer,
    update_mingreateraffixcount,
    weapon_slot_name_hint,
)
from src.gui.importer.import_pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import extract_mobalytics_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True

BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
BUILD_SCRIPT_PREFIX = "window.__PRELOADED_STATE__="
CHARM_ICON_SET_SLUG_REGEX = re.compile(r"/charms/(?P<slug>[^/?#]+?)(?:\.[^/.?#]+)?(?:[?#]|$)")
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
PROFILE_GUIDE_BASE_URL = f"{BUILD_GUIDE_BASE_URL}profile"
SCRIPT_XPATH = "//script"
ITEM_TOOLTIP_CSS = "[data-tippy-root]"

if TYPE_CHECKING:
    from selenium.webdriver.chromium.webdriver import ChromiumDriver
    from selenium.webdriver.remote.webelement import WebElement


class MobalyticsError(Exception):
    pass


@retry_importer(inject_webdriver=True)
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
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    variant_id = url.split(",")[1].split("#")[0] if "activeVariantId" in url else None
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)
    # The build is shoved in a massive JSON in one of the script tags. We find that json now.
    scripts_elem = raw_html_data.xpath(SCRIPT_XPATH)
    full_script_data_json = None
    for script in scripts_elem:
        if script.text and script.text.strip().startswith(BUILD_SCRIPT_PREFIX):
            full_script_data_json = json.loads(script.text.strip().replace(BUILD_SCRIPT_PREFIX, "")[:-1])
            break

    if not full_script_data_json:
        _log_mobalytics_page_diagnostics(driver=driver, page_source=page_source, script_count=len(scripts_elem))
        LOGGER.error(
            msg
            := "No script containing build data was found. This means Mobalytics has changed how they present data, please submit a bug."
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

    finished_filters: list[ItemFilterModel] = []
    finished_filter_name_hints: list[str | None] = []
    charm_filters = []
    seal_filters = []
    aspect_upgrade_filters = []
    guessed_set_name = None
    for item in sorted(items, key=lambda item: jsonpath.findall(".gameEntity.type", item)[0] != "charms"):
        item_filter = ItemFilterModel()
        entity_type = jsonpath.findall(".gameEntity.type", item)[0]
        if entity_type not in ["aspects", "uniqueItems", "charms", "seals", "items"]:
            continue
        title_result = jsonpath.findall(".gameEntity.entity.title", item) or jsonpath.findall(".gameEntity.title", item)
        item_name = str(title_result[0]).strip() if title_result else ""
        if not item_name:
            slot_result = jsonpath.findall(".gameSlotSlug", item)
            LOGGER.warning(
                f"Skipping {slot_result[0] if slot_result else '(unknown slot)'} ({entity_type}) because it has no title."
            )
            continue
        slot_result = jsonpath.findall(".gameSlotSlug", item)
        if not slot_result or not (slot_type := str(slot_result[0]).strip()):
            LOGGER.error(msg := f"No slot type found for {item_name}")
            raise MobalyticsError(msg)
        raw_affixes = (
            jsonpath.findall(".gameEntity.modifiers.gearStats[*]", item)
            + jsonpath.findall(".gameEntity.modifiers.sealStats[*]", item)
            + jsonpath.findall(".gameEntity.modifiers.charmStats[*]", item)
        )
        raw_inherents = jsonpath.findall(".gameEntity.modifiers.implicitStats[*]", item)
        raw_affixes = [x for x in raw_affixes if x is not None]
        raw_inherents = [x for x in raw_inherents if x is not None]

        is_unique = entity_type == "uniqueItems"
        if is_unique:
            try:
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=item_name)]
            except Exception:
                LOGGER.exception(f"Unexpected error adding unique aspect for {item_name}, please report a bug.")

        legendary_aspect = _get_legendary_aspect(item_name)
        if legendary_aspect:
            aspect_upgrade_filters.append(legendary_aspect)

        if (
            entity_type not in ["charms", "seals"]
            and not raw_affixes
            and not raw_inherents
            and not item_filter.unique_aspect
        ):
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

        if "seal" in slot_type.lower():
            item_type = ItemType.HoradricSeal
        elif "charm" in slot_type.lower():
            item_type = ItemType.Charm
        else:
            item_type = (
                match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot_type))
                if item_type is None
                else item_type
            )
        if item_type is None and is_weapon:
            item_type = _get_weapon_type_from_slot_tooltip(driver=driver, slot_type=slot_type)
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

        affixes = _convert_raw_to_affixes(
            raw_affixes, config.import_greater_affixes, item_type, guessed_set_name=guessed_set_name
        )
        inherents = _convert_raw_to_affixes(raw_inherents, item_type=item_type, guessed_set_name=guessed_set_name)

        if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
            seal_charm_filters = charm_filters if item_type == ItemType.Charm else seal_filters
            seal_charm_model = CharmFilterModel if item_type == ItemType.Charm else SealFilterModel
            # Extract unique aspect and set info for charms
            charm_unique_aspect = None
            charm_set_name = None
            if item_type == ItemType.Charm:
                normalized_item_name = correct_name(item_name)
                if normalized_item_name in Dataloader().aspect_unique_dict:
                    charm_unique_aspect = normalized_item_name
                charm_set_name = _extract_mobalytics_charm_set_name(item)
            if not affixes and not charm_unique_aspect and not charm_set_name:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes, unique aspect, or set name.")
                continue
            seal_charm_filter = create_seal_charm_filter(
                affixes=affixes,
                require_gas=config.require_greater_affixes,
                model_type=seal_charm_model,
                unique_name=charm_unique_aspect,
                set_name=charm_set_name,
            )
            seal_charm_filters.append(seal_charm_filter)
            if isinstance(seal_charm_filter, CharmFilterModel) and not guessed_set_name and seal_charm_filter.set:
                guessed_set_name = seal_charm_filter.set[0]
            continue

        if affixes:
            affixes = sorted(affixes, key=lambda affix: (affix.name, affix.type.value))
            item_filter.affix_pool = create_item_affix_pool(affixes=affixes, unique_like=is_unique)
            update_mingreateraffixcount(item_filter, config.require_greater_affixes)
        item_filter.min_power = 100
        if inherents:
            inherents = sorted(inherents, key=lambda affix: (affix.name, affix.type.value))
            item_filter.inherent_pool = [
                AffixFilterCountModel(count=[AffixFilterModel(name=x.name) for x in inherents])
            ]
        finished_filters.append(item_filter)
        finished_filter_name_hints.append(weapon_slot_name_hint(item_filter, _humanize_mobalytics_slot(slot_type)))

    ImportPipeline.run(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="mobalytics",
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
                        paragon_steps=extract_mobalytics_paragon_steps(
                            paragon_data if isinstance(paragon_data, dict) else {}
                        ),
                        paragon_build_name=build_name,
                    )
                ],
            ),
        ),
        config=config,
    )


def _corrections(input_str: str) -> str:
    match input_str.lower():
        case "max life":
            return "maximum life"
    return input_str


def _fix_input_url(url: str) -> str:
    return unquote(url)


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


def _humanize_mobalytics_slot(slot_type: str) -> str:
    """Turn a gameSlotSlug into the human-readable label mobalytics itself shows (e.g. "dual-wield-weapon-1" -> "Dual wield weapon 1")."""
    return slot_type.replace("-", " ").capitalize()


def _get_weapon_slot_trigger(driver: ChromiumDriver, slot_type: str) -> WebElement | None:
    """Find the hoverable element for a weapon slot, keyed off its human-readable title.

    Mobalytics markup uses hashed, non-semantic class names, so slots are instead located by the
    `title` attribute mobalytics derives from the item's gameSlotSlug.
    """
    slot_title = _humanize_mobalytics_slot(slot_type)
    try:
        return driver.find_element(By.XPATH, f"//span[@title='{slot_title}']/ancestor::div[@data-tippy-delegate-id][1]")
    except NoSuchElementException:
        return None


def _get_weapon_type_from_slot_tooltip(driver: ChromiumDriver, slot_type: str) -> ItemType | None:
    """Hover a weapon's paperdoll icon to read its type from the tooltip.

    Mobalytics only reveals a weapon's type this way for unique/mythic items; generic legendary
    weapons (aspect only) show a tooltip with no type info, so this returns None for those.
    """
    trigger = _get_weapon_slot_trigger(driver=driver, slot_type=slot_type)
    if trigger is None:
        return None
    tooltip_html = hover_and_get_tooltip_html(
        driver=driver, element=trigger, tooltip_css=ITEM_TOOLTIP_CSS, warn_on_timeout=False
    )
    if not tooltip_html:
        return None
    tooltip = lxml.html.fromstring(tooltip_html)
    type_nodes = tooltip.xpath("(.//p)[2]")
    if not type_nodes:
        return None
    return fix_weapon_type(input_str=" ".join(type_nodes[0].text_content().split()))


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


def _extract_mobalytics_charm_set_name(item: dict) -> str | None:
    icon_url = (jsonpath.findall(".gameEntity.iconUrl", item) or [""])[0]
    match = CHARM_ICON_SET_SLUG_REGEX.search(str(icon_url))
    if not match:
        return None

    set_candidate = correct_name(match.group("slug").replace("-", " "))
    if set_candidate in Dataloader().set_list:
        return set_candidate

    compact_candidate = set_candidate.replace("_", "").replace("-", "")
    return next(
        (
            set_name
            for set_name in Dataloader().set_list
            if set_name.replace("_", "").replace("-", "") == compact_candidate
        ),
        None,
    )


def _convert_raw_to_affixes(
    raw_stats: list[dict],
    import_greater_affixes=False,
    item_type: ItemType | None = None,
    guessed_set_name: str | None = None,
) -> list[Affix]:
    result = []
    affix_dict = affix_dict_for_item_type(item_type=item_type)
    for stat in raw_stats:
        if stat:
            stat_id = stat["id"]

            stat_clean = clean_str(_corrections(input_str=stat_id.replace("-", " ")))
            matched_name = None
            if item_type == ItemType.HoradricSeal and guessed_set_name:
                # First check if the stat is a generic affix with an exact or very close match
                best_global_key = closest_match(stat_clean, affix_dict)
                is_exact_generic = False
                if best_global_key and best_global_key != "damage":
                    global_display = affix_dict[best_global_key]
                    if rapidfuzz.distance.Levenshtein.distance(stat_clean, global_display) <= 2:
                        # Ensure it's not a set-specific affix of another set
                        is_set_specific = False
                        for set_name in Dataloader().set_list:
                            if best_global_key.startswith(set_name + "_"):
                                is_set_specific = True
                                break
                        if not is_set_specific:
                            is_exact_generic = True
                            matched_name = best_global_key

                if not is_exact_generic:
                    set_keys = {
                        k: v for k, v in Dataloader().seal_affix_dict.items() if k.startswith(guessed_set_name + "_")
                    }
                    potential_match = closest_match(stat_clean, set_keys)
                    if potential_match:
                        display_name = Dataloader().seal_affix_dict[potential_match]
                        if rapidfuzz.fuzz.token_set_ratio(stat_clean, display_name) >= 50:
                            matched_name = potential_match
            if matched_name is None:
                matched_name = closest_match(stat_clean, affix_dict)

            affix_obj = Affix(name=matched_name)
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {stat=}")
                continue
            if import_greater_affixes and stat.get("isGreater", False):
                affix_obj.type = AffixType.greater
            result.append(affix_obj)
    return result


if __name__ == "__main__":
    src.logger.setup()
    from src.gui.importer.gui_common import setup_webdriver

    driver = setup_webdriver()

    URLS = ["https://mobalytics.gg/diablo-4/builds/auradin-holy-light-aura-paladin"]
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
