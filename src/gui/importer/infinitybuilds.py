import dataclasses
import json
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import lxml.html
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
    create_seal_charm_filter,
    get_with_retry,
    match_to_enum,
    retry_importer,
    update_mingreateraffixcount,
)
from src.gui.importer.import_pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import (
    InfinityBuildsParagonCatalog,
    extract_infinitybuilds_paragon_steps,
    fetch_infinitybuilds_paragon_catalog,
)
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

if TYPE_CHECKING:
    from selenium.webdriver.chromium.webdriver import ChromiumDriver

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://infinitybuilds.gg/"
TOOLS_API_BASE_URL = "https://tools.infinitybuilds.gg/api/games/diablo4/build-data"
SCRIPT_XPATH = "//script"
NEXT_F_PUSH_REGEX = re.compile(r"^self\.__next_f\.push\(\[(?:\d+),(\".*\")\]\)\s*;?\s*$", re.DOTALL)
ASPECT_UPGRADE_RARITIES = {"legendary"}
CATALOG_ID_INSTANCE_PREFIX = re.compile(r"^(item|aspect)-\d+-")


class InfinityBuildsError(Exception):
    pass


@retry_importer(inject_webdriver=True)
def import_infinitybuilds(config: ImportConfig, driver: ChromiumDriver = None):
    url = config.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use an infinitybuilds.gg build link")
        return
    LOGGER.info(f"Loading {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    # The build data is streamed in via React Server Components after initial hydration, so wait
    # for it to actually show up in the page source instead of just the first script tag. Note the
    # embedded JSON is itself JSON-string-encoded, so quotes appear escaped (\"classId\") here.
    wait.until(lambda d: "classId" in d.page_source and "variants" in d.page_source)
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)

    build_header = _extract_build_title(raw_html_data)
    build_data = _extract_build_data(raw_html_data)
    if build_data is None:
        LOGGER.error(
            msg := "No script containing build data was found. This means InfinityBuilds has changed how they "
            "present data, please submit a bug."
        )
        raise InfinityBuildsError(msg)

    class_name = build_data.get("classId", "")
    if not class_name:
        LOGGER.error(msg := "No class name found")
        raise InfinityBuildsError(msg)

    variants = build_data.get("variants") or []
    variants = [v for v in variants if v.get("gear")]
    if not variants:
        LOGGER.error(msg := "No gear found for this build")
        raise InfinityBuildsError(msg)

    # InfinityBuilds URLs don't let you pick a specific variant, so import all of them
    if len(variants) > 1:
        LOGGER.info(f"This build has {len(variants)} variants, importing all of them.")

    # Resolve all variants' gear in a single API call to avoid redundant round trips.
    resolved = _resolve_gear_data(class_name, [piece for variant in variants for piece in variant["gear"]])

    paragon_catalog: InfinityBuildsParagonCatalog | None = None
    if config.export_paragon:
        try:
            paragon_catalog = fetch_infinitybuilds_paragon_catalog()
        except Exception:
            LOGGER.warning(
                "Could not fetch InfinityBuilds paragon catalog data, skipping paragon export.", exc_info=True
            )

    extracted_variants = []
    for variant in variants:
        extracted_variant = _build_variant_for_gear(gear=variant["gear"], resolved=resolved, config=config)
        extracted_variant.name = variant.get("name", "")
        if paragon_catalog is not None:
            extracted_variant.paragon_steps = extract_infinitybuilds_paragon_steps(
                variant.get("paragon") or {}, paragon_catalog, class_name
            )
        extracted_variant.paragon_build_name = build_header or extracted_variant.name
        extracted_variants.append(extracted_variant)

    ImportPipeline.run(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="infinitybuilds",
                class_name=class_name,
                build_header=build_header,
                variants=extracted_variants,
            ),
        ),
        config=config,
    )


def _build_variant_for_gear(gear: list[dict], resolved: _ResolvedGearData, config: ImportConfig) -> Variant:
    finished_filters = []
    charm_filters = []
    seal_filters = []
    mythic_names = []
    aspect_upgrade_filters = []
    for gear_piece in gear:
        item_id = _canonical_catalog_id(gear_piece.get("itemId"))
        item = resolved.items.get(item_id, {})
        item_name = item.get("label", "")
        if not item_name:
            LOGGER.warning(f"Skipping {gear_piece.get('slot')} because no item name was resolved.")
            continue
        rarity = item.get("rarity", "")

        if rarity == "mythic":
            mythic_names.append(item_name)
            continue

        # Use the resolved catalog slot name (e.g. "Sword", "Ring", "Chest Armor") rather than the
        # build's internal slot key (e.g. "mainhand", "ring1", "chest") which doesn't map 1:1.
        catalog_slot = item.get("slot", "")
        item_type = match_to_enum(ItemType, catalog_slot)
        if item_type is None:
            LOGGER.warning(f"Couldn't match item_type for slot {catalog_slot!r}. Please edit manually")

        aspect_id = _canonical_catalog_id(gear_piece.get("aspectId"))
        aspect_name = resolved.aspects.get(aspect_id, {}).get("label") if aspect_id else None
        if aspect_name and rarity in ASPECT_UPGRADE_RARITIES and config.import_aspect_upgrades:
            normalized_aspect_name = _normalize_aspect_name(aspect_name)
            if normalized_aspect_name in Dataloader().aspect_list:
                aspect_upgrade_filters.append(normalized_aspect_name)
            else:
                LOGGER.warning(
                    f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades."
                )

        affixes = _convert_raw_to_affixes(
            gear_piece.get("affixes") or [], resolved.affixes, config.import_greater_affixes, item_type=item_type
        )

        if item_type in (ItemType.HoradricSeal, ItemType.Charm):
            seal_charm_filters = charm_filters if item_type == ItemType.Charm else seal_filters
            seal_charm_model = CharmFilterModel if item_type == ItemType.Charm else SealFilterModel
            unique_name = item_name if rarity == "unique" else None
            if not affixes and not unique_name:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes or unique aspect.")
                continue
            seal_charm_filters.append(
                create_seal_charm_filter(
                    affixes=affixes,
                    require_gas=config.require_greater_affixes,
                    model_type=seal_charm_model,
                    unique_name=unique_name,
                )
            )
            continue

        item_filter = ItemFilterModel()
        item_filter.item_type = [item_type] if item_type else []
        if rarity == "unique":
            item_filter.unique_aspect = [AspectUniqueFilterModel(name=item_name)]
        if not affixes:
            LOGGER.warning(f"Skipping {gear_piece.get('slot')} because it had no supported affixes.")
            continue
        affixes = sorted(affixes, key=lambda affix: (affix.name, affix.type.value))
        item_filter.affix_pool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=x.name, want_greater=x.type == AffixType.greater) for x in affixes],
                min_count=1 if rarity == "unique" else 3,
            )
        ]
        update_mingreateraffixcount(item_filter, config.require_greater_affixes)
        item_filter.min_power = 100
        finished_filters.append(item_filter)

    return Variant(
        affix_filters=finished_filters,
        charm_filters=charm_filters,
        seal_filters=seal_filters,
        aspect_upgrade_filters=aspect_upgrade_filters,
        mythic_names=mythic_names,
    )


def _extract_build_title(raw_html_data: lxml.html.HtmlElement) -> str:
    title_elems = raw_html_data.xpath("//title")
    if title_elems and title_elems[0].text:
        # Page titles look like "Build Name | InfinityBuilds"
        return title_elems[0].text.split("|")[0].strip()
    return ""


def _extract_build_data(raw_html_data: lxml.html.HtmlElement) -> dict | None:
    """InfinityBuilds ships build data inside a React Flight script chunk.

    Each matching ``<script>`` tag looks like ``self.__next_f.push([id, "<json-string>"])``. The
    pushed value is itself a JSON-encoded string, so ``json.loads`` on it yields the real
    (properly unescaped) page content, inside which we bracket-match the ``"variants":[...]`` array.
    """
    for script in raw_html_data.xpath(SCRIPT_XPATH):
        if not script.text or "self.__next_f.push" not in script.text or "classId" not in script.text:
            continue
        match = NEXT_F_PUSH_REGEX.match(script.text.strip())
        if not match:
            continue
        try:
            content = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        variants_key = '"variants":['
        key_idx = content.find(variants_key)
        if key_idx == -1:
            continue
        array_start = key_idx + len(variants_key) - 1
        try:
            variants_raw = _extract_balanced(content, array_start, "[", "]")
            variants = json.loads(variants_raw)
        except ValueError, json.JSONDecodeError:
            continue
        class_id_match = re.search(r'"classId":"([a-z]+)"', content)
        return {"classId": class_id_match.group(1) if class_id_match else "", "variants": variants}
    return None


def _extract_balanced(text: str, start_idx: int, open_ch: str, close_ch: str) -> str:
    depth = 0
    in_string = False
    escape = False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]
    msg = "Unbalanced brackets while extracting InfinityBuilds data"
    raise ValueError(msg)


@dataclasses.dataclass
class _ResolvedGearData:
    items: dict[str, dict]
    aspects: dict[str, dict]
    affixes: dict[str, dict]


def _canonical_catalog_id(raw_id: str | None) -> str | None:
    """Strip extra numeric value from catalog id.

    Some build variants embed gear with an extra numeric instance id spliced into the item/aspect
    which the catalog returned by the API doesn't have. Strip it before lookups.

    """
    return CATALOG_ID_INSTANCE_PREFIX.sub(r"\1-", raw_id) if raw_id else raw_id


def _resolve_gear_data(class_name: str, gear: list[dict]) -> _ResolvedGearData:
    item_ids = sorted({_canonical_catalog_id(g["itemId"]) for g in gear if g.get("itemId")})
    aspect_ids = sorted({_canonical_catalog_id(g["aspectId"]) for g in gear if g.get("aspectId")})
    affix_ids = sorted({affix["affixId"] for g in gear for affix in (g.get("affixes") or []) if affix.get("affixId")})

    params = {"classId": class_name, "mode": "view", "shape": "2", "locale": "en"}
    if item_ids:
        params["itemIds"] = ",".join(item_ids)
    if aspect_ids:
        params["aspectIds"] = ",".join(aspect_ids)
    if affix_ids:
        params["affixIds"] = ",".join(affix_ids)

    response = get_with_retry(f"{TOOLS_API_BASE_URL}?{urlencode(params)}")
    dataset = response.json().get("dataset", {})
    gear_data = dataset.get("gear", {})

    return _ResolvedGearData(
        items={item["id"]: item for item in gear_data.get("items", [])},
        aspects={aspect["id"]: aspect for aspect in gear_data.get("aspects", [])},
        affixes={affix["id"]: affix for affix in gear_data.get("affixes", [])},
    )


def _normalize_aspect_name(name: str) -> str:
    # Aspect names in our data drop the word "aspect" itself (e.g. "Edgemaster's Aspect" -> "edgemasters").
    return correct_name(name.lower().replace("aspect", "").strip())


def _convert_raw_to_affixes(
    raw_affixes: list[dict],
    resolved_affixes: dict[str, dict],
    import_greater_affixes: bool = False,
    item_type: ItemType | None = None,
) -> list[Affix]:
    result = []
    affix_dict = affix_dict_for_item_type(item_type=item_type)
    for raw_affix in raw_affixes:
        if raw_affix.get("tempered"):
            continue
        affix_id = raw_affix.get("affixId")
        resolved_affix = resolved_affixes.get(affix_id)
        if not resolved_affix or not resolved_affix.get("label"):
            LOGGER.error(f"Couldn't resolve {affix_id=}")
            continue
        stat_clean = clean_str(resolved_affix["label"])
        matched_name = closest_match(stat_clean, affix_dict)
        if matched_name is None:
            LOGGER.error(f"Couldn't match {resolved_affix['label']=}")
            continue
        affix_obj = Affix(name=matched_name)
        if import_greater_affixes and resolved_affix.get("greaterAffixEligible"):
            value_range = resolved_affix.get("valueRange") or {}
            max_value = value_range.get("max")
            if max_value is not None and raw_affix.get("value", 0) >= max_value:
                affix_obj.type = AffixType.greater
        result.append(affix_obj)
    return result


if __name__ == "__main__":
    src.logger.setup()
    from src.gui.importer.gui_common import setup_webdriver

    driver = setup_webdriver()

    URLS = ["https://infinitybuilds.gg/en/builds/barbarian-fL8P6vVSqI"]
    for X in URLS:
        run_config = ImportConfig(
            url=X,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=False,
            require_greater_affixes=False,
            export_paragon=True,
            custom_file_name=None,
        )
        import_infinitybuilds(run_config, driver)
