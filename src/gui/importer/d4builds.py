import datetime
import hashlib
import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlsplit, urlunsplit

import lxml.html
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
from src.gui.importer.common import (
    add_to_profiles,
    fix_offhand_type,
    fix_weapon_type,
    get_class_name,
    match_to_enum,
    retry_importer,
    save_as_profile,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_d4builds_paragon_steps
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


class D4BuildsException(Exception):
    pass


@dataclass(slots=True)
class D4BuildsVariantOption:
    """Represents one selectable D4Builds variant URL."""

    url: str
    label: str


@retry_importer(inject_webdriver=True)
def import_d4builds(config: ImportConfig, driver: ChromiumDriver = None):
    """Import one or more D4Builds variants into d4lf profiles."""
    target_urls = _resolve_target_urls(config)
    if not target_urls:
        LOGGER.error("Invalid url, please use a d4builds url")
        return
    if config.selected_variant_urls is not None:
        LOGGER.info(f"Importing {len(target_urls)} selected D4Builds variant(s).")

    created_profiles: list[str] = []
    for target_url in target_urls:
        corrected_file_name = _import_d4builds_url(
            config=config, driver=driver, url=target_url, import_count=len(target_urls)
        )
        if corrected_file_name:
            created_profiles.append(corrected_file_name)

    if created_profiles:
        LOGGER.info(f"Finished importing {len(created_profiles)} D4Builds profile(s)")
    else:
        LOGGER.warning("No D4Builds profiles were imported")


def get_d4builds_variant_options(url: str) -> list[D4BuildsVariantOption]:
    """Return importable D4Builds variant URLs for the provided build page."""
    normalized_url = url.strip().replace("\n", "")
    if BASE_URL not in normalized_url:
        LOGGER.error("Invalid url, please use a d4builds url")
        return []

    parsed_url = urlsplit(normalized_url)
    current_variant_values = parse_qs(parsed_url.query).get("var", [])
    if current_variant_values:
        base_url = _get_d4builds_variant_discovery_url(normalized_url)
        return [
            D4BuildsVariantOption(
                url=_set_d4builds_variant_value(base_url=base_url, variant_value=str(variant_index)),
                label=f"Var {variant_index}",
            )
            for variant_index in range(7)
        ]

    current_variant_url = _normalize_d4builds_variant_url(normalized_url)
    current_variant_label = _build_d4builds_variant_label(raw_label="", variant_url=current_variant_url)
    return [D4BuildsVariantOption(url=current_variant_url, label=current_variant_label)]


def _resolve_target_urls(config: ImportConfig) -> list[str]:
    """Resolve which D4Builds URLs should be imported."""
    if config.selected_variant_urls is not None:
        unique_urls: list[str] = []
        for url in config.selected_variant_urls:
            if url and url not in unique_urls:
                unique_urls.append(url)
        return unique_urls
    url = config.url.strip().replace("\n", "")
    if BASE_URL not in url:
        return []
    return [url]


def _import_d4builds_url(config: ImportConfig, driver: ChromiumDriver, url: str, import_count: int) -> str | None:
    """Import a single D4Builds URL into a d4lf profile."""
    LOGGER.info(f"Loading {url}")
    _load_d4builds_page(driver=driver, url=url)
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
                if any(substring in affix_name.lower() for substring in ["focus", "offhand", "shield", "totem"]):
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
                and not any(substring in affix_name.lower() for substring in ["elements"])
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

    selected_variant_parts = _get_selected_variant_labels_from_driver(driver=driver)
    file_name = _resolve_output_file_name(
        config=config,
        data=data,
        class_name=class_name,
        source_url=url,
        selected_variant_parts=selected_variant_parts,
        import_count=import_count,
    )

    paragon_step_count = 0
    if config.export_paragon:
        steps = extract_d4builds_paragon_steps(driver, class_name=class_name)
        if steps:
            paragon_step_count = len(steps)
            profile.Paragon = build_paragon_profile_payload(
                build_name=file_name, source_url=url, paragon_boards_list=steps
            )
        else:
            LOGGER.warning("Paragon export enabled, but no paragon data was found on this D4Builds page.")

    corrected_file_name = save_as_profile(file_name=file_name, profile=profile, url=url)
    if paragon_step_count:
        LOGGER.info(f"Paragon imported successfully for {corrected_file_name} with {paragon_step_count} board step(s).")
    if config.add_to_profiles:
        add_to_profiles(corrected_file_name)

    return corrected_file_name


def _load_d4builds_page(driver: ChromiumDriver, url: str) -> None:
    """Load a D4Builds page and wait until the build UI is present."""
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
    wait.until(EC.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
    time.sleep(5)


def _extract_d4builds_variant_options(driver: ChromiumDriver, source_url: str) -> list[D4BuildsVariantOption]:
    """Extract distinct D4Builds variant URLs from the live DOM."""
    raw_options = _read_d4builds_variant_links_from_driver(driver=driver)
    if not raw_options:
        return []

    current_variant_url = _normalize_d4builds_variant_url(source_url)
    options: list[D4BuildsVariantOption] = []
    seen_urls: set[str] = set()
    for raw_option in raw_options:
        if not isinstance(raw_option, dict):
            continue
        raw_url = str(raw_option.get("url", "")).strip()
        variant_url = _normalize_d4builds_variant_url(urljoin(source_url, raw_url)) if raw_url else current_variant_url
        if not variant_url or variant_url in seen_urls:
            continue
        seen_urls.add(variant_url)
        label = _build_d4builds_variant_label(
            raw_label=str(raw_option.get("label", "")).strip(), variant_url=variant_url
        )
        options.append(D4BuildsVariantOption(url=variant_url, label=label))

    options.sort(key=lambda option: _get_d4builds_variant_sort_key(option.url))
    return options


def _get_d4builds_variant_discovery_url(url: str) -> str:
    """Return the base D4Builds build URL used to discover all variant links."""
    parsed_url = urlsplit(url.strip())
    query_params = parse_qs(parsed_url.query)
    query_params.pop("var", None)
    discovery_query = urlencode([(key, value) for key, values in query_params.items() for value in values])
    return urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path.rstrip("/"), discovery_query, ""))


def _probe_d4builds_variant_options(driver: ChromiumDriver, source_url: str) -> list[D4BuildsVariantOption]:
    """Probe numbered D4Builds ``?var=`` URLs when the DOM does not expose variant links."""
    base_url = _get_d4builds_variant_discovery_url(source_url)
    options: list[D4BuildsVariantOption] = []
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    consecutive_misses = 0

    for variant_index in range(12):
        probe_url = _set_d4builds_variant_value(base_url=base_url, variant_value=str(variant_index))
        requested_variant_value = str(variant_index)
        try:
            _load_d4builds_page(driver=driver, url=probe_url)
        except Exception:
            LOGGER.debug("Failed to probe D4Builds variant url %s", probe_url, exc_info=True)
            if options:
                consecutive_misses += 1
                if consecutive_misses >= 3:
                    break
            continue

        data = lxml.html.fromstring(driver.page_source)
        resolved_url = _normalize_d4builds_variant_url(driver.current_url or probe_url)
        resolved_variant_values = parse_qs(urlparse(resolved_url).query).get("var", [])
        resolved_variant_value = resolved_variant_values[0] if resolved_variant_values else ""
        normalized_probe_url = _normalize_d4builds_variant_url(probe_url)

        if resolved_variant_value and resolved_variant_value != requested_variant_value:
            consecutive_misses += 1
            if options and consecutive_misses >= 3:
                break
            continue

        if normalized_probe_url in seen_urls:
            consecutive_misses += 1
            if options and consecutive_misses >= 3:
                break
            continue

        fingerprint = _get_d4builds_variant_fingerprint(driver=driver, data=data, source_url=normalized_probe_url)
        selected_variant_parts = _get_selected_variant_labels_from_driver(driver=driver)
        class_name = _get_build_class_name(data=data, source_url=normalized_probe_url)
        label = _build_d4builds_probed_variant_label(
            data=data,
            class_name=class_name,
            source_url=normalized_probe_url,
            selected_variant_parts=selected_variant_parts,
        )

        allow_duplicate_fingerprint = bool(resolved_variant_value == requested_variant_value)
        if fingerprint in seen_fingerprints and not allow_duplicate_fingerprint:
            consecutive_misses += 1
            if options and consecutive_misses >= 3:
                break
            continue

        options.append(D4BuildsVariantOption(url=normalized_probe_url, label=label))
        seen_urls.add(normalized_probe_url)
        seen_fingerprints.add(fingerprint)
        consecutive_misses = 0

    return _deduplicate_d4builds_variant_labels(options)


def _set_d4builds_variant_value(base_url: str, variant_value: str) -> str:
    """Return ``base_url`` with the provided ``var`` query value applied."""
    parsed_url = urlsplit(base_url)
    query_params = parse_qs(parsed_url.query)
    query_items = [(key, value) for key, values in query_params.items() if key != "var" for value in values]
    query_items.append(("var", variant_value))
    return urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path.rstrip("/"), urlencode(query_items), ""))


def _get_d4builds_variant_fingerprint(driver: ChromiumDriver, data: lxml.html.HtmlElement, source_url: str) -> str:
    """Return a stable fingerprint for the currently loaded D4Builds variant."""
    fingerprint_parts = [
        *_get_selected_variant_labels_from_driver(driver=driver),
        *_get_header_file_name_parts(data),
        *_iter_text_candidates(data.xpath(BUILD_OVERVIEW_XPATH)),
        *_iter_text_candidates(data.xpath(PAPERDOLL_XPATH)),
        *_get_title_file_name_parts(data=data, source_url=source_url),
    ]
    fingerprint_source = "\n".join(part for part in fingerprint_parts if part)
    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


def _build_d4builds_probed_variant_label(
    data: lxml.html.HtmlElement, class_name: str, source_url: str, selected_variant_parts: list[str] | None
) -> str:
    """Build a readable label for a probed D4Builds variant URL."""
    if selected_variant_parts:
        selected_label = " / ".join(selected_variant_parts)
        if selected_label:
            return selected_label

    file_name_parts = _get_file_name_parts(
        data=data, class_name=class_name, source_url=source_url, selected_variant_parts=selected_variant_parts
    )
    if file_name_parts:
        return " / ".join(file_name_parts)
    return _build_d4builds_variant_label(raw_label="", variant_url=source_url)


def _deduplicate_d4builds_variant_labels(options: list[D4BuildsVariantOption]) -> list[D4BuildsVariantOption]:
    """Append a var suffix when multiple D4Builds variants share the same label."""
    label_counts: dict[str, int] = {}
    for option in options:
        label_counts[option.label] = label_counts.get(option.label, 0) + 1

    deduplicated_options: list[D4BuildsVariantOption] = []
    for option in options:
        label = option.label
        if label_counts.get(label, 0) > 1:
            variant_suffix = _get_variant_suffix_from_url(option.url).replace("_", " ").title()
            if variant_suffix:
                label = f"{label} ({variant_suffix})"
        deduplicated_options.append(D4BuildsVariantOption(url=option.url, label=label))
    return deduplicated_options


def _read_d4builds_variant_links_from_driver(driver: ChromiumDriver) -> list[dict[str, str]]:
    """Read candidate D4Builds variant links from the live DOM."""
    script = r"""
const elements = document.querySelectorAll('a[href*="?var="], a[href*="&var="]');
const results = [];
const seen = new Set();
for (const element of elements) {
  const href = element.href || element.getAttribute('href') || '';
  if (!href || !href.includes('var=')) {
    continue;
  }
  if (seen.has(href)) {
    continue;
  }
  seen.add(href);
  const text = (element.textContent || '').replace(/\s+/g, ' ').trim();
  results.push({url: href, label: text});
}
return results;
"""
    try:
        raw_options = driver.execute_script(script)
    except Exception:
        LOGGER.exception("Failed to read D4Builds variant links from the DOM.")
        return []
    if not isinstance(raw_options, list):
        return []
    return raw_options


def _normalize_d4builds_variant_url(url: str) -> str:
    """Return a stable D4Builds variant URL without fragments."""
    parsed_url = urlsplit(url)
    filtered_query = parse_qs(parsed_url.query).get("var", [])
    query = urlencode({"var": filtered_query[0]}) if filtered_query else parsed_url.query
    return urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path.rstrip("/"), query, ""))


def _build_d4builds_variant_label(raw_label: str, variant_url: str) -> str:
    """Build a human-readable label for a D4Builds variant URL."""
    normalized_label = _normalize_text(raw_label)
    if normalized_label and normalized_label.casefold() not in {"gear & skills", "share", "save build"}:
        return normalized_label
    variant_suffix = _get_variant_suffix_from_url(variant_url)
    if variant_suffix:
        return variant_suffix.replace("_", " ").title()
    return "Current build"


def _get_d4builds_variant_sort_key(url: str) -> tuple[int, str]:
    """Return a stable sort key for D4Builds variant URLs."""
    variant_values = parse_qs(urlparse(url).query).get("var", [])
    if variant_values and variant_values[0].isdigit():
        return int(variant_values[0]), url
    return 9999, url


def _resolve_output_file_name(
    config: ImportConfig,
    data: lxml.html.HtmlElement,
    class_name: str,
    source_url: str,
    selected_variant_parts: list[str] | None,
    import_count: int,
) -> str:
    """Resolve the output file name for a D4Builds import."""
    if not config.custom_file_name:
        return _build_default_file_name(
            data=data, class_name=class_name, source_url=source_url, selected_variant_parts=selected_variant_parts
        )

    if import_count <= 1:
        return config.custom_file_name

    suffix_parts = _get_file_name_parts(
        data=data, class_name=class_name, source_url=source_url, selected_variant_parts=selected_variant_parts
    )
    suffix = "_".join(suffix_parts) if suffix_parts else _get_variant_suffix_from_url(source_url) or "variant"
    return f"{config.custom_file_name}_{suffix}"


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
    normalized_class_name = class_name if class_name and class_name != "Unknown" else "Unknown"
    if file_name_parts:
        return f"d4builds_{normalized_class_name}_{'_'.join(file_name_parts)}"
    timestamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y_%m_%d_%H_%M_%S")
    return f"d4builds_{normalized_class_name}_{timestamp}"


def _get_file_name_parts(
    data: lxml.html.HtmlElement, class_name: str, source_url: str, selected_variant_parts: list[str] | None = None
) -> list[str]:
    """Extract descriptive build labels for the saved profile name."""
    parts = [*_get_header_file_name_parts(data), *(selected_variant_parts or []), *_get_selected_variant_parts(data)]
    if not parts:
        parts.extend(_get_title_file_name_parts(data=data, source_url=source_url))
    deduplicated_parts = []
    for part in parts:
        if not _is_useful_file_name_part(part=part, class_name=class_name):
            continue
        if part not in deduplicated_parts:
            deduplicated_parts.append(part)

    variant_suffix = _get_variant_suffix_from_url(source_url)
    if variant_suffix and variant_suffix not in deduplicated_parts:
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


def _get_selected_variant_labels_from_driver(driver: ChromiumDriver) -> list[str]:
    """Read selected variant labels from the live DOM when D4Builds renders them client-side."""
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
  '.builder__header__description',
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
    normalized_parts = []
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
