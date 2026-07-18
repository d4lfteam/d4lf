import logging
import re
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote

import jsonpath
import lxml.html
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By

from src.importing._conversion import as_text as _as_text  # ruff:ignore[unused-import]
from src.importing._filters import affix_dict_for_item_type, fix_weapon_type, match_set_aware_seal_affix
from src.importing._web import hover_and_get_tooltip_html
from src.item import Affix, AffixType, Dataloader, ItemType
from src.perception import clean_str, closest_match
from src.scripts import correct_name

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

LOGGER = logging.getLogger(__name__)
CHARM_ICON_SET_SLUG_REGEX = re.compile(r"/charms/(?P<slug>[^/?#]+?)(?:\.[^/.?#]+)?(?:[?#]|$)")
ITEM_TOOLTIP_CSS = "[data-tippy-root]"
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
type _JsonPathValue = str | int | float | bool | list[object] | dict[str, object] | None


def _corrections(input_str: str) -> str:
    match input_str.lower():
        case "max life":
            return "maximum life"
    return input_str


def _fix_input_url(url: str) -> str:
    return unquote(url)


def _first_jsonpath_result(path: str, value: object) -> object | None:
    results = jsonpath.findall(path, cast("_JsonPathValue", value))
    if not isinstance(results, list) or not results:
        return None
    return results[0]


def _log_mobalytics_page_diagnostics(driver: WebDriver, page_source: str, script_count: int) -> None:
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


def _read_mobalytics_driver_value(driver: WebDriver, value_name: str) -> str:
    try:
        value = getattr(driver, value_name)
    except WebDriverException as exc:
        return f"<unavailable: {exc.__class__.__name__}>"
    return str(value)


def _extract_mobalytics_season_number(full_script_data_json: Mapping[str, object]) -> str:
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


def _get_weapon_slot_trigger(driver: WebDriver, slot_type: str) -> WebElement | None:
    """Find the hoverable element for a weapon slot, keyed off its human-readable title.

    Mobalytics markup uses hashed, non-semantic class names, so slots are instead located by the
    `title` attribute mobalytics derives from the item's gameSlotSlug.
    """
    slot_title = _humanize_mobalytics_slot(slot_type)
    try:
        return driver.find_element(By.XPATH, f"//span[@title='{slot_title}']/ancestor::div[@data-tippy-delegate-id][1]")
    except NoSuchElementException:
        return None


def _get_weapon_type_from_slot_tooltip(driver: WebDriver, slot_type: str) -> ItemType | None:
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
        if aspect_name is None:
            return ""
        if aspect_name not in Dataloader().aspect_list:
            LOGGER.warning(
                f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
            )
        else:
            return aspect_name
    return ""


def _extract_mobalytics_charm_set_name(item: Mapping[str, object]) -> str | None:
    icon_url = (jsonpath.findall(".gameEntity.iconUrl", item) or [""])[0]
    match = CHARM_ICON_SET_SLUG_REGEX.search(str(icon_url))
    if not match:
        return None
    set_candidate = correct_name(match.group("slug").replace("-", " "))
    if set_candidate is None:
        return None
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
    raw_stats: Sequence[Mapping[str, object]],
    import_greater_affixes: bool = False,
    item_type: ItemType | None = None,
    guessed_set_name: str | None = None,
) -> list[Affix]:
    result = []
    affix_dict = affix_dict_for_item_type(item_type=item_type)
    for stat in raw_stats:
        if stat:
            stat_id = stat.get("id")
            if not isinstance(stat_id, str):
                continue
            stat_clean = clean_str(_corrections(input_str=stat_id.replace("-", " ")))
            matched_name = None
            if item_type == ItemType.HoradricSeal and guessed_set_name:
                matched_name = match_set_aware_seal_affix(
                    stat_clean=stat_clean, affix_dict=affix_dict, guessed_set_name=guessed_set_name
                )
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
