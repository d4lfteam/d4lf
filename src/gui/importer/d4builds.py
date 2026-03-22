import datetime
import logging
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import lxml.html
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import src.logger
from src.config.models import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    ItemFilterModel,
    ProfileModel,
    UniqueModel,
)
from src.dataloader import Dataloader
from src.gui.importer.gui_common import (
    build_default_profile_name,
    fix_offhand_type,
    fix_weapon_type,
    get_class_name,
    log_import_summary,
    match_to_enum,
    retry_importer,
    save_imported_profile,
    setup_webdriver,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig, ImportVariantOption
from src.gui.importer.paragon_export import attach_paragon_payload, extract_d4builds_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

if TYPE_CHECKING:
    from selenium.webdriver.chromium.webdriver import ChromiumDriver

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://d4builds.gg/builds"
BUILD_OVERVIEW_XPATH = "//*[@class='builder__stats__list']"
CLASS_XPATH = "//*[contains(@class, 'builder__header__description')]"
ITEM_GROUP_XPATH = ".//*[contains(@class, 'builder__stats__group')]"
ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__stats__slot')]"
ITEM_STATS_XPATH = ".//*[contains(@class, 'dropdown__button__wrapper')]"
GA_XPATH = ".//*[contains(@class, 'greater__affix__button--filled')]"
PAPERDOLL_ITEM_SLOT_XPATH = ".//*[contains(@class, 'builder__gear__slot')]"
PAPERDOLL_ITEM_UNIQUE_NAME_XPATH = ".//*[contains(@class, 'builder__gear__name--')]"
PAPERDOLL_ITEM_XPATH = ".//*[contains(@class, 'builder__gear__item') and not(contains(@class, 'disabled'))]"
PAPERDOLL_LEGENDARY_ASPECT_XPATH = (
    "//*[@class='builder__gear__name' and not(contains(@class, 'builder__gear__name--'))]"
)
PAPERDOLL_XPATH = "//*[contains(@class, 'builder__gear__items')]"
TEMPERING_ICON_XPATH = ".//*[contains(@src, 'tempering_02.png')]"
SANCTIFIED_ICON_XPATH = ".//*[contains(@src, 'sanctified_icon.png')]"
UNIQUE_ICON_XPATH = ".//*[contains(@src, '/Uniques/')]"
VARIANT_PROBE_PADDING = 6
VARIANT_PROBE_MINIMUM_MAX_ID = 3
VARIANT_PROBE_TIMEOUT_SECONDS = 4
VARIANT_PROBE_MAX_CONSECUTIVE_MISSES = 1


class D4BuildsException(Exception):
    pass


@retry_importer(inject_webdriver=True)
def import_d4builds(config: ImportConfig, driver: ChromiumDriver = None):
    url = config.url.strip().replace("\n", "")
    if BASE_URL not in url:
        LOGGER.error("Invalid url, please use a d4builds url")
        return
    wait = WebDriverWait(driver, 10)
    variant_ids = _resolve_variant_ids_to_import(config=config, driver=driver, source_url=url, wait=wait)
    import_count = len(variant_ids)
    created_profiles: list[str] = []
    for variant_id in variant_ids:
        variant_url = _build_variant_url(source_url=url, variant_id=variant_id)
        corrected_file_name = _import_d4builds_variant(
            config=config, driver=driver, url=variant_url, wait=wait, import_count=import_count
        )
        if corrected_file_name:
            created_profiles.append(corrected_file_name)
    log_import_summary(LOGGER, "D4Builds", created_profiles)


def get_d4builds_variant_options(url: str) -> list[ImportVariantOption]:
    driver = setup_webdriver()
    try:
        wait = WebDriverWait(driver, 10)
        _wait_for_d4builds_page(driver=driver, source_url=url, wait=wait)
        return _load_variant_options(driver=driver, source_url=url)
    finally:
        driver.quit()


def _resolve_variant_ids_to_import(
    config: ImportConfig, driver: ChromiumDriver, source_url: str, wait: WebDriverWait
) -> list[str | None]:
    if not config.import_multiple_variants:
        return [_get_variant_index_from_url(source_url)]

    if config.selected_variants:
        return list(config.selected_variants)

    _wait_for_d4builds_page(driver=driver, source_url=source_url, wait=wait)
    variant_options = _load_variant_options(driver=driver, source_url=source_url)
    if variant_options:
        return [variant.id for variant in variant_options]
    return [_get_variant_index_from_url(source_url)]


def _load_variant_options(driver: ChromiumDriver, source_url: str) -> list[ImportVariantOption]:
    """Load D4Builds variant options from the live DOM, then fall back to probing ?var= URLs."""
    variants = _read_variant_options_from_driver(driver)
    if len(variants) > 1:
        return variants

    probed_variants = _probe_variant_options_by_url(driver=driver, source_url=source_url, known_variants=variants)
    return probed_variants if len(probed_variants) > len(variants) else variants


def _build_variant_url(source_url: str, variant_id: str | None) -> str:
    if variant_id is None:
        return source_url

    parsed_url = urlparse(source_url)
    query_params = parse_qs(parsed_url.query, keep_blank_values=True)
    query_params["var"] = [variant_id]
    return urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))


def _wait_for_d4builds_page(driver: ChromiumDriver, source_url: str, wait: WebDriverWait) -> None:
    LOGGER.info(f"Loading {source_url}")
    driver.get(source_url)
    wait.until(EC.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
    wait.until(EC.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
    _wait_for_selected_variant(driver=driver, wait=wait, source_url=source_url)
    time.sleep(
        5
    )  # super hacky but I didn't find anything else. The page is not fully loaded when the above wait is done


def _read_variant_options_from_driver(driver: ChromiumDriver) -> list[ImportVariantOption]:
    variants = _query_variant_options_from_driver(driver)
    if len(variants) > 1:
        return variants

    if _expand_variant_dropdown(driver):
        for _ in range(10):
            time.sleep(0.1)
            variants = _query_variant_options_from_driver(driver)
            if len(variants) > 1:
                return variants

    return variants


def _expand_variant_dropdown(driver: ChromiumDriver) -> bool:
    """Best-effort expand of the D4Builds variant dropdown before reading options."""
    selectors = (
        ".build-variant-dropdown .dropdown__button button",
        ".variant__navigation .item__arrow__icon--variant",
        ".build-variant-dropdown .dropdown__button",
        ".variant__navigation .dropdown__button",
    )
    for selector in selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                element.click()
            except Exception:
                try:
                    driver.execute_script(
                        """
const element = arguments[0];
for (const eventName of ["pointerdown", "mousedown", "mouseup", "click"]) {
  element.dispatchEvent(new MouseEvent(eventName, { bubbles: true, cancelable: true, view: window }));
}
""",
                        element,
                    )
                except Exception:
                    LOGGER.debug(
                        "Failed to click D4Builds variant dropdown element for selector %s.", selector, exc_info=True
                    )
                else:
                    return True
            else:
                return True
    return False


def _query_variant_options_from_driver(driver: ChromiumDriver) -> list[ImportVariantOption]:
    """Read D4Builds variant options that are currently present in the DOM."""
    script = """
const selectors = [
  "input[id^='renameVariant']",
  ".variant__navigation *",
  ".build-variant-dropdown *",
  "[role='listbox'] *",
  "[role='menu'] *",
  ".dropdown__menu *",
  ".dropdown__content *",
  ".dropdown__list *",
];
const elements = [];
const seenElements = new Set();
for (const selector of selectors) {
  for (const element of document.querySelectorAll(selector)) {
    if (!seenElements.has(element)) {
      seenElements.add(element);
      elements.push(element);
    }
  }
}
const textOf = (value) => (value || "").replace(/\\s+/g, " ").trim();
return elements.map((element) => {
  const nestedInput = element.matches("input[id^='renameVariant']")
    ? element
    : element.querySelector("input[id^='renameVariant']");
  return {
    id: nestedInput ? nestedInput.id : (element.id || ""),
    label: textOf(
      (nestedInput && (nestedInput.value || nestedInput.getAttribute("value"))) ||
      element.getAttribute("aria-label") ||
      element.getAttribute("title") ||
      element.textContent ||
      ""
    ),
    href: element.getAttribute("href") || "",
    onclick: element.getAttribute("onclick") || "",
    data_variant: element.getAttribute("data-variant") || "",
    data_variant_id: element.getAttribute("data-variant-id") || "",
    data_variant_value: element.getAttribute("data-value") || "",
  };
});
"""
    try:
        raw_variants = driver.execute_script(script)
    except Exception:
        LOGGER.exception("Failed to read D4Builds variant options from the DOM.")
        return []
    return _normalize_variant_options(raw_variants)


def _normalize_variant_options(raw_variants: object) -> list[ImportVariantOption]:
    """Normalize raw D4Builds variant DOM records into unique importer options."""
    if not isinstance(raw_variants, list):
        return []

    variants = []
    seen_ids: set[str] = set()
    for index, variant in enumerate(raw_variants, start=1):
        if not isinstance(variant, dict):
            continue
        variant_id = _normalize_variant_id(
            variant.get("id"),
            variant.get("data_variant"),
            variant.get("data_variant_id"),
            variant.get("data_variant_value"),
            variant.get("href"),
            variant.get("onclick"),
        )
        if not variant_id or variant_id in seen_ids:
            continue
        label = _normalize_text(str(variant.get("label", "")).strip()) or f"variant_{index}"
        variants.append(ImportVariantOption(id=variant_id, label=label))
        seen_ids.add(variant_id)
    return variants


def _normalize_variant_id(*candidates: object) -> str:
    """Extract a D4Builds variant index from DOM attributes or URLs."""
    for candidate in candidates:
        if candidate is None:
            continue
        text = str(candidate).strip()
        if not text:
            continue
        if match := re.search(r"renameVariant(\d+)", text, re.IGNORECASE):
            return match.group(1)
        if match := re.search(r"(?:^|[?&])var=(\d+)(?:$|[&#])", text):
            return match.group(1)
        if text.isdigit():
            return text
    return ""


def _probe_variant_options_by_url(
    driver: ChromiumDriver,
    source_url: str,
    known_variants: list[ImportVariantOption] | tuple[ImportVariantOption, ...] = (),
) -> list[ImportVariantOption]:
    """Probe sequential D4Builds ?var= URLs to discover variants when the dropdown DOM is incomplete."""
    discovered_variants = {variant.id: variant for variant in known_variants}
    consecutive_misses = 0
    for variant_id in _get_variant_probe_ids(source_url=source_url, known_variants=known_variants):
        if variant_id in discovered_variants:
            continue
        if variant := _probe_variant_option(driver=driver, source_url=source_url, variant_id=variant_id):
            discovered_variants[variant.id] = variant
            consecutive_misses = 0
            continue
        consecutive_misses += 1
        if consecutive_misses >= VARIANT_PROBE_MAX_CONSECUTIVE_MISSES:
            break
    return sorted(discovered_variants.values(), key=_sort_variant_option)


def _get_variant_probe_ids(
    source_url: str, known_variants: list[ImportVariantOption] | tuple[ImportVariantOption, ...] = ()
) -> list[str]:
    """Build a small sequential list of D4Builds variant ids to probe."""
    current_variant_index = _get_variant_index_from_url(source_url)
    highest_known_variant = max(
        (int(variant.id) for variant in known_variants if str(variant.id).isdigit()), default=-1
    )
    highest_starting_point = max(
        int(current_variant_index) if current_variant_index and current_variant_index.isdigit() else -1,
        highest_known_variant,
    )
    max_variant_id = max(VARIANT_PROBE_MINIMUM_MAX_ID, highest_starting_point + VARIANT_PROBE_PADDING)
    return [str(index) for index in range(max_variant_id + 1)]


def _probe_variant_option(driver: ChromiumDriver, source_url: str, variant_id: str) -> ImportVariantOption | None:
    """Load a D4Builds ?var= URL and return the rendered label when that variant exists."""
    variant_url = _build_variant_url(source_url=source_url, variant_id=variant_id)
    try:
        driver.get(variant_url)
        wait = WebDriverWait(driver, VARIANT_PROBE_TIMEOUT_SECONDS)
        wait.until(EC.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
        wait.until(EC.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
        wait.until(lambda current_driver: bool(_read_variant_label_from_driver(current_driver, variant_id)))
    except TimeoutException:
        return None
    except Exception:
        LOGGER.debug("Unexpected error while probing D4Builds variant var=%s", variant_id, exc_info=True)
        return None

    variant_label = _normalize_text(_read_variant_label_from_driver(driver, variant_id))
    if not variant_label:
        return None
    return ImportVariantOption(id=variant_id, label=variant_label)


def _sort_variant_option(variant: ImportVariantOption) -> tuple[int, str]:
    """Sort numeric D4Builds variant ids before any non-numeric fallbacks."""
    return (0, f"{int(variant.id):04d}") if variant.id.isdigit() else (1, variant.id)


def _import_d4builds_variant(
    config: ImportConfig, driver: ChromiumDriver, url: str, wait: WebDriverWait, import_count: int
) -> str:
    _wait_for_d4builds_page(driver=driver, source_url=url, wait=wait)
    data = lxml.html.fromstring(driver.page_source)
    class_name = _get_build_class_name(data=data, source_url=url)
    if not (items := data.xpath(BUILD_OVERVIEW_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsException(msg)
    slot_to_unique_name_map = _get_item_slots(data=data)
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = _get_legendary_aspects(data=data)
    for item in items[0]:
        item_filter = ItemFilterModel()
        if not (slot := item.xpath(ITEM_SLOT_XPATH)[1].tail):
            LOGGER.error("No item_type found")
            continue
        if slot not in slot_to_unique_name_map:
            LOGGER.warning(f"Empty slots are not supported. Skipping: {slot}")
            continue
        if not (stats := item.xpath(ITEM_STATS_XPATH)):
            LOGGER.error(f"No stats found for {slot=}")
            continue
        item_type = None
        affixes = []
        inherents = []

        if slot_to_unique_name_map[slot]:
            unique_model = UniqueModel()
            unique_name = slot_to_unique_name_map[slot]
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=unique_name)
                # We just can't trust their data well enough so removing this just like the other importers.
                # unique_model.affix = [AffixFilterModel(name=x.name) for x in affixes]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(
                    f"Unexpected error importing unique {unique_name}, please report a bug and include a link to the build you were trying to import."
                )
            continue

        is_weapon = "weapon" in slot.lower()
        for stat in stats:
            if stat.xpath(TEMPERING_ICON_XPATH) or stat.xpath(SANCTIFIED_ICON_XPATH):
                continue
            if "filled" not in stat.xpath("../..")[0].attrib["class"]:
                continue
            affix_name = _get_affix_name(stat=stat)
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
            affix_obj = Affix(
                name=closest_match(clean_str(_corrections(input_str=affix_name)), Dataloader().affix_dict)
            )
            if affix_obj.name is None:
                LOGGER.error(f"Couldn't match {affix_name=}")
                continue
            if config.import_greater_affixes and stat.xpath("../../../..")[0].xpath(GA_XPATH):
                affix_obj.type = AffixType.greater
            if (
                "ring" in slot.lower()
                and any(substring in affix_name.lower() for substring in ["resistance"])
                and not any(
                    substring in affix_name.lower() for substring in ["elements"]
                )  # Exclude resistance to all elements
            ) or (
                "boots" in slot.lower()
                and any(substring in affix_name.lower() for substring in ["max evade charges", "attacks reduce"])
            ):
                inherents.append(affix_obj)
            else:
                affixes.append(affix_obj)

        if not affixes:
            continue

        item_type = (
            match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot.replace(" ", "")))
            if item_type is None
            else item_type
        )
        if item_type is None:
            if is_weapon:
                LOGGER.warning(
                    f"Couldn't find an item_type for weapon slot {slot}, defaulting to all weapon types instead."
                )
                item_filter.itemType = WEAPON_TYPES
            else:
                item_filter.itemType = []
                LOGGER.warning(f"Couldn't match item_type: {slot}. Please edit manually")
        else:
            item_filter.itemType = [item_type]
        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=x.name, want_greater=x.type == AffixType.greater) for x in affixes],
                minCount=3,
            )
        ]
        item_filter.minPower = 100
        update_mingreateraffixcount(item_filter, config.require_greater_affixes)
        if inherents:
            item_filter.inherentPool = [AffixFilterCountModel(count=[AffixFilterModel(name=x.name) for x in inherents])]
        filter_name_template = item_filter.itemType[0].name if item_type else slot.replace(" ", "")
        filter_name = filter_name_template
        i = 2
        while any(filter_name == next(iter(x)) for x in finished_filters):
            filter_name = f"{filter_name_template}{i}"
            i += 1
        finished_filters.append({filter_name: item_filter})
    profile = ProfileModel(name="imported profile", Affixes=sorted(finished_filters, key=lambda x: next(iter(x))))
    if config.import_uniques and unique_filters:
        profile.Uniques = unique_filters
    if config.import_aspect_upgrades and aspect_upgrade_filters:
        profile.AspectUpgrades = aspect_upgrade_filters

    selected_variant_parts = _get_selected_variant_labels_from_driver(driver=driver, source_url=url)

    file_name = _resolve_output_file_name(
        config=config,
        data=data,
        class_name=class_name,
        source_url=url,
        selected_variant_parts=selected_variant_parts,
        import_count=import_count,
    )

    if config.export_paragon:
        attach_paragon_payload(
            profile,
            build_name=file_name,
            source_url=url,
            paragon_boards_list=extract_d4builds_paragon_steps(driver, class_name=class_name),
            missing_data_message="Paragon export enabled, but no paragon data was found on this D4Builds page.",
        )

    return save_imported_profile(
        file_name=file_name, profile=profile, url=url, add_to_active_profiles=config.add_to_profiles
    )


def _get_build_class_name(data: lxml.html.HtmlElement, source_url: str) -> str:
    """Extract the class name from multiple possible page locations."""
    class_candidates = [
        *_iter_text_candidates(data.xpath("//title")),
        *_iter_text_candidates(data.xpath("//h1")),
        *_get_url_path_candidates(data=data, source_url=source_url),
        *_iter_text_candidates(data.xpath(CLASS_XPATH + "/*")),
        *_iter_text_candidates(data.xpath(CLASS_XPATH)),
    ]
    for candidate in class_candidates:
        class_name = get_class_name(candidate)
        if class_name != "Unknown":
            return class_name
    LOGGER.error(f"Couldn't match class name from any source: {class_candidates=}")
    return "Unknown"


def _iter_text_candidates(elements: list[lxml.html.HtmlElement]) -> list[str]:
    """Return normalized text candidates from a list of HTML elements."""
    candidates = []
    for element in elements:
        if not hasattr(element, "text_content"):
            continue
        candidate = " ".join(element.text_content().split())
        if candidate:
            candidates.append(candidate)
    return candidates


def _get_url_path_candidates(data: lxml.html.HtmlElement, source_url: str) -> list[str]:
    """Return normalized candidates derived from canonical URLs and the source URL."""
    candidates = []
    for xpath in ("//link[@rel='canonical']/@href", "//meta[@property='og:url']/@content"):
        for url in data.xpath(xpath):
            candidate = _normalize_url_candidate(url)
            if candidate:
                candidates.append(candidate)
    if source_url:
        candidate = _normalize_url_candidate(source_url)
        if candidate:
            candidates.append(candidate)
    return candidates


def _normalize_url_candidate(url: str) -> str:
    """Convert a build URL path into text that can be matched against class names."""
    match = re.search(r"/builds/([^/?#]+)", url)
    if not match:
        return ""
    return match.group(1).replace("-", " ").strip()


def _build_default_file_name(
    data: lxml.html.HtmlElement, class_name: str, source_url: str, selected_variant_parts: list[str] | None = None
) -> str:
    """Build a human-readable default profile name from page labels before falling back to a timestamp."""
    file_name_parts = _get_file_name_parts(
        data=data, class_name=class_name, source_url=source_url, selected_variant_parts=selected_variant_parts
    )
    fallback = (
        class_name
        if class_name and class_name != "Unknown"
        else datetime.datetime.now(tz=datetime.UTC).strftime("%Y_%m_%d_%H_%M_%S")
    )
    return build_default_profile_name("d4builds", *file_name_parts, fallback=fallback)


def _resolve_output_file_name(
    config: ImportConfig,
    data: lxml.html.HtmlElement,
    class_name: str,
    source_url: str,
    selected_variant_parts: list[str] | None,
    import_count: int,
) -> str:
    if not config.custom_file_name:
        return _build_default_file_name(
            data=data, class_name=class_name, source_url=source_url, selected_variant_parts=selected_variant_parts
        )
    if import_count <= 1:
        return config.custom_file_name

    variant_suffix_parts = list(selected_variant_parts or [])
    if not variant_suffix_parts:
        variant_suffix = _get_variant_suffix_from_url(source_url)
        if variant_suffix:
            variant_suffix_parts.append(variant_suffix)
    return build_default_profile_name(config.custom_file_name, *variant_suffix_parts, fallback="variant")


def _get_file_name_parts(
    data: lxml.html.HtmlElement, class_name: str, source_url: str, selected_variant_parts: list[str] | None = None
) -> list[str]:
    """Extract descriptive build labels for the saved profile name."""
    html_selected_variant_parts = _get_selected_variant_parts(data)
    parts = [*_get_header_file_name_parts(data), *(selected_variant_parts or []), *html_selected_variant_parts]
    if not parts:
        parts.extend(_get_title_file_name_parts(data=data, source_url=source_url))
    deduplicated_parts = []
    for part in parts:
        if not _is_useful_file_name_part(part=part, class_name=class_name):
            continue
        if part not in deduplicated_parts:
            deduplicated_parts.append(part)

    variant_suffix = _get_variant_suffix_from_url(source_url)
    if (
        variant_suffix
        and not selected_variant_parts
        and not html_selected_variant_parts
        and variant_suffix not in deduplicated_parts
    ):
        deduplicated_parts.append(variant_suffix)

    return deduplicated_parts


def _get_header_file_name_parts(data: lxml.html.HtmlElement) -> list[str]:
    """Extract distinct header labels, preserving separate variant labels when available."""
    parts = []
    for header in data.xpath(CLASS_XPATH):
        element_parts = _extract_element_label_parts(header)
        if element_parts:
            parts.extend(element_parts)
    return parts


def _get_selected_variant_parts(data: lxml.html.HtmlElement) -> list[str]:
    """Extract currently selected variant labels from generic selected-state markup."""
    xpaths = (
        "//*[(@aria-selected='true' or @data-state='active') and not(self::script)]",
        "//*[contains(@class, 'selected') and not(self::script)]",
    )
    parts = []
    for xpath in xpaths:
        for element in data.xpath(xpath):
            text = _normalize_text(" ".join(element.itertext()))
            if text:
                parts.append(text)
    return parts


def _get_variant_index_from_url(source_url: str) -> str | None:
    """Return the D4Builds variant index encoded in the URL, if present."""
    if not source_url:
        return None
    variant_values = parse_qs(urlparse(source_url).query).get("var", [])
    return variant_values[0].strip() if variant_values and variant_values[0].strip() else None


def _read_variant_label_from_driver(driver: ChromiumDriver, variant_index: str) -> str:
    """Read the live D4Builds variant label from the DOM for a specific variant index."""
    script = """
const input = document.querySelector(arguments[0]);
if (!input) {
  return '';
}
return (input.value || input.getAttribute('value') || input.textContent || '').replace(/\\s+/g, ' ').trim();
"""
    try:
        result = driver.execute_script(script, f"#renameVariant{variant_index}")
    except Exception:
        LOGGER.debug("Failed to read D4Builds variant label for var=%s", variant_index, exc_info=True)
        return ""
    return result.strip() if isinstance(result, str) else ""


def _wait_for_selected_variant(driver: ChromiumDriver, wait: WebDriverWait, source_url: str) -> None:
    """Best-effort wait until the variant from the URL has rendered in the live DOM."""
    variant_index = _get_variant_index_from_url(source_url)
    if variant_index is None:
        return
    try:
        wait.until(lambda current_driver: bool(_read_variant_label_from_driver(current_driver, variant_index)))
    except Exception:
        LOGGER.debug("Timed out waiting for the D4Builds variant label for var=%s", variant_index, exc_info=True)


def _get_selected_variant_labels_from_driver(driver: ChromiumDriver, source_url: str = "") -> list[str]:
    """Read selected variant labels from the live DOM when D4Builds renders them client-side."""
    normalized_parts = []
    variant_index = _get_variant_index_from_url(source_url)
    if variant_index is not None:
        variant_label = _normalize_text(_read_variant_label_from_driver(driver, variant_index))
        if variant_label:
            return [variant_label]

    script = r"""
const selectors = [
  '[role="tab"][aria-selected="true"]',
  '[role="option"][aria-selected="true"]',
  '[aria-current="true"]',
  '[data-state="active"]',
  '[data-state="checked"]',
  '.selected',
  '.active',
  '.is-active',
];
const texts = [];
for (const selector of selectors) {
  for (const element of document.querySelectorAll(selector)) {
    const text = (element.textContent || '').replace(/\s+/g, ' ').trim();
    if (text) {
      texts.push(text);
    }
  }
}
return texts;
"""
    try:
        raw_parts = driver.execute_script(script)
    except Exception:
        LOGGER.exception("Failed to read selected variant labels from the D4Builds DOM.")
        return []
    if not isinstance(raw_parts, list):
        return []
    for part in raw_parts:
        if not isinstance(part, str):
            continue
        normalized_part = _normalize_text(part)
        if normalized_part and normalized_part not in normalized_parts:
            normalized_parts.append(normalized_part)
    return normalized_parts


def _get_title_file_name_parts(data: lxml.html.HtmlElement, source_url: str) -> list[str]:
    """Fallback to the page title or URL slug when header labels are not available."""
    title_candidates = []
    for raw_title in data.xpath("//title/text()"):
        title = _clean_build_title(raw_title)
        if title:
            title_candidates.append(title)
    if title_candidates:
        return title_candidates
    url_candidate = _normalize_url_candidate(source_url)
    return [url_candidate.title()] if url_candidate else []


def _extract_element_label_parts(element: lxml.html.HtmlElement) -> list[str]:
    """Return per-child text labels so variant and sub-variant names stay separate."""
    parts = []
    leading_text = _normalize_text(element.text or "")
    if leading_text:
        parts.append(leading_text)
    for child in element:
        child_text = _normalize_text(" ".join(child.itertext()))
        if child_text:
            parts.append(child_text)
        tail_text = _normalize_text(child.tail or "")
        if tail_text:
            parts.append(tail_text)
    if not parts:
        fallback_text = _normalize_text(" ".join(element.itertext()))
        if fallback_text:
            parts.append(fallback_text)
    return parts


def _clean_build_title(title: str) -> str:
    """Strip generic suffixes from the page title so only the build label remains."""
    cleaned_title = _normalize_text(title)
    for suffix in ("· D4 Builds", "- D4 Builds", "- Diablo 4"):
        if cleaned_title.endswith(suffix):
            cleaned_title = cleaned_title.removesuffix(suffix).rstrip(" -")
    return re.sub(r"\s+Build Guide$", "", cleaned_title).strip()


def _normalize_text(text: str) -> str:
    """Collapse whitespace in extracted UI labels."""
    return " ".join(text.split())


def _get_variant_suffix_from_url(source_url: str) -> str:
    """Return a stable suffix derived from the D4Builds variant query parameter."""
    if not source_url:
        return ""
    parsed_url = urlparse(source_url)
    variant_values = parse_qs(parsed_url.query).get("var", [])
    if not variant_values:
        return ""
    variant_value = variant_values[0].strip()
    if not variant_value:
        return ""
    return f"var_{variant_value}"


def _is_useful_file_name_part(part: str, class_name: str) -> bool:
    """Filter out generic, duplicate, or class-only labels from the generated file name."""
    normalized_part = _normalize_text(part).strip("-–— ")
    if not normalized_part:
        return False
    lowered_part = normalized_part.casefold()
    ignored_parts = {
        "none",
        "updated on .",
        "share",
        "save build",
        "gear & skills",
        "skill tree",
        "paragon",
        "mercenaries",
    }
    if lowered_part in ignored_parts:
        return False
    if class_name and lowered_part == class_name.casefold():
        return False
    return not (
        lowered_part in {"barbarian", "druid", "necromancer", "rogue", "sorcerer", "spiritborn", "paladin"}
        and len(normalized_part.split()) <= 2
    )


def _get_affix_name(stat: lxml.html.HtmlElement) -> str:
    """Extract visible affix text even when wrapped in nested markup."""
    for span in stat.xpath("./span"):
        affix_name = " ".join(span.text_content().split())
        if affix_name:
            return affix_name
    return ""


def _corrections(input_str: str) -> str:
    input_str = input_str.lower()
    match input_str:
        case "max life":
            return "maximum life"
        case "total armor":
            return "armor"
    if "ranks to" in input_str or "ranks of" in input_str or "ranks" in input_str:
        return input_str.replace("ranks to", "to").replace("ranks of", "to").replace("ranks", "to")
    return input_str


def _get_item_slots(data: lxml.html.HtmlElement) -> dict[str, str]:
    result = {}
    if not (paperdoll := data.xpath(PAPERDOLL_XPATH)):
        LOGGER.error(msg := "No paperdoll found")
        raise D4BuildsException(msg)
    if not (items := paperdoll[0].xpath(PAPERDOLL_ITEM_XPATH)):
        LOGGER.error(msg := "No items found")
        raise D4BuildsException(msg)
    for item in items:
        if item.xpath(PAPERDOLL_ITEM_SLOT_XPATH):
            slot = item.xpath(PAPERDOLL_ITEM_SLOT_XPATH)[0].text
            if slot == "2H Weapon":  # This happens when a build has a weapon and no offhand
                slot = "Weapon"
            unique_name = item.xpath(PAPERDOLL_ITEM_UNIQUE_NAME_XPATH)
            result[slot] = unique_name[0].text if unique_name else ""
    return result


def _get_legendary_aspects(data: lxml.html.HtmlElement) -> list[str]:
    result = []
    if not (paperdoll := data.xpath(PAPERDOLL_XPATH)):
        # Shouldn't happen, earlier code would have thrown an exception
        return result

    aspects = paperdoll[0].xpath(PAPERDOLL_LEGENDARY_ASPECT_XPATH)
    for aspect in aspects:
        aspect_name = correct_name(aspect.text.lower().replace("aspect", "").strip())

        if aspect_name not in Dataloader().aspect_list:
            LOGGER.warning(
                f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
            )
        else:
            result.append(aspect_name)

    return result


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://d4builds.gg/builds/e3aab60e-15a0-47ee-99ec-648788901104/?var=1"]
    for X in URLS:
        config = ImportConfig(
            url=X,
            import_uniques=True,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            export_paragon=False,
            custom_file_name=None,
        )
        import_d4builds(config)
