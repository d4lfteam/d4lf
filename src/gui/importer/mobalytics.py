import json
import logging
import re
from urllib.parse import parse_qs, unquote, urlparse

import jsonpath
import lxml.html

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
    add_to_profiles,
    build_default_profile_name,
    fix_offhand_type,
    fix_weapon_type,
    get_with_retry,
    log_import_summary,
    match_to_enum,
    retry_importer,
    save_as_profile,
    update_mingreateraffixcount,
)
from src.gui.importer.importer_config import ImportConfig, ImportVariantOption
from src.gui.importer.paragon_export import build_paragon_profile_payload, extract_mobalytics_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
SCRIPT_XPATH = "//script"
BUILD_SCRIPT_PREFIX = "window.__PRELOADED_STATE__="


class MobalyticsException(Exception):
    pass


@retry_importer
def import_mobalytics(config: ImportConfig):
    url, full_script_data_json, root_document_name, build_name, class_name = _load_mobalytics_build_context(config.url)
    variant_id = _extract_variant_id_from_url(url)
    variants = _get_variants(root_document_name=root_document_name, full_script_data_json=full_script_data_json)
    created_profiles: list[str] = []

    if variants:
        variants_to_import = _resolve_variants_to_import(
            variants=variants, selected_variant_id=variant_id, config=config
        )
    else:
        selected_variant, selected_variant_id = _get_selected_variant(
            root_document_name=root_document_name, full_script_data_json=full_script_data_json, variant_id=variant_id
        )
        variants_to_import = [(selected_variant, selected_variant_id)]

    for variant, resolved_variant_id in variants_to_import:
        items = variant.get("genericBuilder", {}).get("slots", [])
        variant_name = _extract_variant_name(
            variant=variant, variant_id=resolved_variant_id, full_script_data_json=full_script_data_json
        )

        if not items:
            LOGGER.error(msg := "No items found")
            raise MobalyticsException(msg)

        profile = _build_profile(items=items, class_name=class_name, config=config)
        file_name = _resolve_output_file_name(
            config=config,
            build_name=build_name,
            class_name=class_name,
            variant_name=variant_name,
            variant_id=resolved_variant_id,
            import_count=len(variants_to_import),
        )
        if config.export_paragon:
            steps = extract_mobalytics_paragon_steps(variant if isinstance(variant, dict) else {})
            if steps:
                profile.Paragon = build_paragon_profile_payload(
                    build_name=file_name, source_url=url, paragon_boards_list=steps
                )
                LOGGER.info("Paragon imported successfully")
            else:
                LOGGER.warning("Paragon export enabled, but no paragon data was found for this Mobalytics variant.")

        corrected_file_name = save_as_profile(file_name=file_name, profile=profile, url=url)
        created_profiles.append(corrected_file_name)

        if config.add_to_profiles:
            add_to_profiles(corrected_file_name)

    log_import_summary(LOGGER, "Mobalytics", created_profiles)


def get_mobalytics_variant_options(url: str) -> list[ImportVariantOption]:
    normalized_url, full_script_data_json, root_document_name, build_name, class_name = _load_mobalytics_build_context(
        url
    )
    variants = _get_variants(root_document_name=root_document_name, full_script_data_json=full_script_data_json)
    if not variants:
        implicit_variant_id = _extract_variant_id_from_url(normalized_url) or "current"
        implicit_variant_label = build_name.strip() or class_name.strip().title() or "current_build"
        return [ImportVariantOption(id=implicit_variant_id, label=implicit_variant_label)]

    options = []
    for index, variant in enumerate(variants, start=1):
        variant_id = str(variant.get("id", "")).strip() or f"variant_{index}"
        variant_name = _extract_variant_name(
            variant=variant, variant_id=variant_id, full_script_data_json=full_script_data_json
        )
        options.append(ImportVariantOption(id=variant_id, label=variant_name or f"variant_{index}"))
    return options


def _load_mobalytics_build_context(url: str) -> tuple[str, dict, str, str, str]:
    url = url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        msg = "Invalid Mobalytics URL"
        raise MobalyticsException(msg)
    url = _fix_input_url(url=url)
    LOGGER.info(f"Loading {url}")
    try:
        response = get_with_retry(url=url, custom_headers={})
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build")
        raise MobalyticsException(msg) from exc

    raw_html_data = lxml.html.fromstring(response.text)
    full_script_data_json = _extract_full_script_data(raw_html_data)
    root_document_name = jsonpath.findall("$..['Diablo4Query:{}'].documents..data.__ref", full_script_data_json)[0]
    build_name = jsonpath.findall(f"$..['{root_document_name}'].data.name", full_script_data_json)[0]
    if not build_name:
        LOGGER.error(msg := "No build name found")
        raise MobalyticsException(msg)
    class_name = jsonpath.findall(
        f"$..['{root_document_name}'].tags.data[?@.groupSlug=='class'].name", full_script_data_json
    )[0].lower()
    if not class_name:
        LOGGER.error(msg := "No class name found")
        raise MobalyticsException(msg)
    return url, full_script_data_json, root_document_name, build_name, class_name


def _extract_full_script_data(raw_html_data: lxml.html.HtmlElement) -> dict:
    scripts_elem = raw_html_data.xpath(SCRIPT_XPATH)
    for script in scripts_elem:
        if script.text and script.text.strip().startswith(BUILD_SCRIPT_PREFIX):
            return json.loads(script.text.strip().replace(BUILD_SCRIPT_PREFIX, "")[:-1])
    LOGGER.error(
        msg
        := "No script containing build data was found. This means Mobalytics has changed how they present data, please submit a bung."
    )
    raise MobalyticsException(msg)


def _get_variants(root_document_name: str, full_script_data_json: dict) -> list[dict]:
    return jsonpath.findall(f"$..['{root_document_name}'].data.buildVariants.values[*]", full_script_data_json)


def _resolve_variants_to_import(
    variants: list[dict], selected_variant_id: str | None, config: ImportConfig
) -> list[tuple[dict, str | None]]:
    if not config.import_multiple_variants:
        selected_variant, resolved_variant_id = _select_variant_by_id(variants, selected_variant_id)
        return [(selected_variant, resolved_variant_id)]

    if config.selected_variants:
        variants_by_id = {
            str(variant.get("id", "")).strip(): variant for variant in variants if str(variant.get("id", "")).strip()
        }
        selected_variants = []
        for variant_id in config.selected_variants:
            variant = variants_by_id.get(variant_id)
            if variant is not None:
                selected_variants.append((variant, variant_id))
        if selected_variants:
            return selected_variants

    return [(variant, str(variant.get("id", "")).strip() or None) for variant in variants]


def _select_variant_by_id(variants: list[dict], variant_id: str | None) -> tuple[dict, str | None]:
    if variant_id:
        for variant in variants:
            if variant.get("id") == variant_id:
                return variant, variant_id

    selected_variant = variants[0]
    return selected_variant, str(selected_variant.get("id", "")).strip() or None


def _resolve_output_file_name(
    config: ImportConfig, build_name: str, class_name: str, variant_name: str, variant_id: str | None, import_count: int
) -> str:
    if not config.custom_file_name:
        return _build_default_file_name(build_name, class_name, variant_name, variant_id)
    if import_count <= 1:
        return config.custom_file_name

    variant_suffix = variant_name.strip() or (f"variant_{variant_id}" if variant_id else "variant")
    return build_default_profile_name(config.custom_file_name, variant_suffix)


def _corrections(input_str: str) -> str:
    match input_str.lower():
        case "max life":
            return "maximum life"
    return input_str


def _fix_input_url(url: str) -> str:
    return unquote(url)


def _extract_variant_id_from_url(url: str) -> str | None:
    query = parse_qs(urlparse(url).query)
    for values in query.values():
        for value in values:
            if "activeVariantId," not in value:
                continue
            return value.split("activeVariantId,", maxsplit=1)[1].split("#", maxsplit=1)[0]
    return None


def _get_selected_variant(
    root_document_name: str, full_script_data_json: dict, variant_id: str | None
) -> tuple[dict, str | None]:
    variants = _get_variants(root_document_name=root_document_name, full_script_data_json=full_script_data_json)
    if not variants:
        return {}, variant_id

    return _select_variant_by_id(variants, variant_id)


def _extract_variant_name(variant: dict, variant_id: str | None, full_script_data_json: dict) -> str:
    direct_candidates = [
        variant.get("title"),
        variant.get("name"),
        variant.get("label"),
        variant.get("variantTitle"),
        variant.get("variantName"),
    ]
    for candidate in direct_candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    if variant_id:
        for path in (
            f"..['NgfDocumentCmWidgetContentVariantsV1DataChildVariant:{variant_id}'].title",
            f"..['NgfDocumentCmWidgetContentVariantsV1DataChildVariant:{variant_id}'].name",
            f"$..[?@.id=='{variant_id}'].title",
            f"$..[?@.id=='{variant_id}'].name",
            f"$..[?@.id=='{variant_id}'].label",
        ):
            variant_names = jsonpath.findall(path, full_script_data_json)
            for candidate in variant_names:
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()

    return ""


def _build_default_file_name(build_name: str, class_name: str, variant_name: str, variant_id: str | None) -> str:
    normalized_build_name = build_name.strip()
    normalized_variant_name = variant_name.strip()
    variant_suffix = ""
    if normalized_variant_name and normalized_variant_name.casefold() not in normalized_build_name.casefold():
        variant_suffix = normalized_variant_name
    elif variant_id:
        variant_suffix = f"variant_{variant_id}"

    fallback = class_name.strip().title()
    return build_default_profile_name("mobalytics", normalized_build_name, variant_suffix, fallback=fallback)


def _build_profile(items: list[dict], class_name: str, config: ImportConfig) -> ProfileModel:
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = []
    for item in items:
        item_filter = ItemFilterModel()
        entity_type = jsonpath.findall(".gameEntity.type", item)[0]
        if entity_type not in ["aspects", "uniqueItems"]:
            continue
        if not (item_name := str(jsonpath.findall(".gameEntity.entity.name", item)[0])):
            LOGGER.error(msg := "No item name found")
            raise MobalyticsException(msg)
        if not (slot_type := str(jsonpath.findall(".gameSlotSlug", item)[0])):
            LOGGER.error(msg := "No slot type found")
            raise MobalyticsException(msg)

        raw_affixes = jsonpath.findall(".gameEntity.modifiers.gearStats[*]", item)
        raw_inherents = jsonpath.findall(".gameEntity.modifiers.implicitStats[*]", item)
        if raw_inherents and raw_inherents[0] is None:
            raw_inherents.clear()

        is_unique = entity_type == "uniqueItems"
        if is_unique:
            unique_model = UniqueModel()
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=item_name)
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(f"Unexpected error importing unique {item_name}, please report a bug.")
            continue

        legendary_aspect = _get_legendary_aspect(item_name)
        if legendary_aspect:
            aspect_upgrade_filters.append(legendary_aspect)

        if not raw_affixes and not raw_inherents:
            LOGGER.debug(f"Skipping {slot_type} because it had no stats provided.")
            continue

        item_type = None
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
                item_filter.itemType = WEAPON_TYPES
            else:
                item_filter.itemType = []
                LOGGER.warning(f"Couldn't match item_type: {slot_type}. Please edit manually")
        else:
            item_filter.itemType = [item_type]

        affixes = _convert_raw_to_affixes(raw_affixes, config.import_greater_affixes)
        inherents = _convert_raw_to_affixes(raw_inherents)

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
        filter_name_template = item_filter.itemType[0].name if item_type else slot_type.replace(" ", "")
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
    return profile


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
        affix_obj = Affix(name=closest_match(clean_str(_corrections(input_str=stat["id"])), Dataloader().affix_dict))
        if affix_obj.name is None:
            LOGGER.error(f"Couldn't match {stat=}")
            continue
        if import_greater_affixes and stat.get("isGreater", False):
            affix_obj.type = AffixType.greater
        result.append(affix_obj)
    return result


if __name__ == "__main__":
    src.logger.setup()
    URLS = [
        # No frills and no uniques
        "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb",
        # Is a variant of the one above
        "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb?ws-ngf5-1=activeVariantId%2C7a9c6d51-18e9-4090-a804-7b73ff00879d",
        # This one has no variants at all, just to make sure that works too
        "https://mobalytics.gg/diablo-4/profile/screamheart/builds/15x-thrash-out-of-date",
        # This one has an item type for the weapon
        "https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
        # This has a necro offhand
        "https://mobalytics.gg/diablo-4/builds/necromancer-kripp-golem-summoner",
        # This has two rogue offhand weapons
        "https://mobalytics.gg/diablo-4/builds/rogue-efficientrogue-dance-of-knives?ws-ngf5-1=activeVariantId%2Ca2977139-f3e2-4b13-aa64-82ba69972528",
    ]
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
        import_mobalytics(config)
