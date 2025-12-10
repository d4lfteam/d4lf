import json
import logging
import re
from urllib.parse import unquote

import jsonpath
import lxml.html

import src.logger
from src.config.models import AffixFilterCountModel, AffixFilterModel, AspectUniqueFilterModel, ItemFilterModel, ProfileModel, UniqueModel
from src.dataloader import Dataloader
from src.gui.importer.common import (
    add_to_profiles,
    fix_offhand_type,
    fix_weapon_type,
    get_with_retry,
    match_to_enum,
    retry_importer,
    save_as_profile,
)
from src.gui.importer.importer_config import ImportConfig
from src.item.data.affix import Affix
from src.item.data.item_type import WEAPON_TYPES, ItemType
from src.item.descr.text import clean_str, closest_match
from src.scripts.common import correct_name

LOGGER = logging.getLogger(__name__)

BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
SCRIPT_XPATH = "//script"
BUILD_SCRIPT_PREFIX = "window.__PRELOADED_STATE__="


class MobalyticsException(Exception):
    pass


@retry_importer
def import_mobalytics(config: ImportConfig):
    url = config.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        return
    url = _fix_input_url(url=url)
    LOGGER.info(f"Loading {url}")
    try:
        r = get_with_retry(url=url, custom_headers={})
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build")
        raise MobalyticsException(msg) from exc
    variant_id = url.split(",")[1] if "activeVariantId" in url else None
    raw_html_data = lxml.html.fromstring(r.text)
    # The build is shoved in a massive JSON in one of the script tags. We find that json now.
    scripts_elem = raw_html_data.xpath(SCRIPT_XPATH)
    full_script_data_json = None
    for script in scripts_elem:
        if script.text and script.text.strip().startswith(BUILD_SCRIPT_PREFIX):
            full_script_data_json = json.loads(script.text.strip().replace(BUILD_SCRIPT_PREFIX, "")[:-1])
            break

    if not full_script_data_json:
        LOGGER.error(
            msg
            := "No script containing build data was found. This means Mobalytics has changed how they present data, please submit a bung."
        )
        raise MobalyticsException(msg)

    # This gets the name of the root document, ie the one that will contain the name of the build
    root_document_name = jsonpath.findall("$..['Diablo4Query:{}'].documents..data.__ref", full_script_data_json)[0]
    build_name = jsonpath.findall(f"$..['{root_document_name}'].data.name", full_script_data_json)[0]
    if not build_name:
        LOGGER.error(msg := "No build name found")
        raise MobalyticsException(msg)
    class_name = jsonpath.findall(f"$..['{root_document_name}'].tags.data[?@.groupSlug=='class'].name", full_script_data_json)[0].lower()
    if not class_name:
        LOGGER.error(msg := "No class name found")
        raise MobalyticsException(msg)
    if variant_id:
        items = jsonpath.findall(
            f"$..['{root_document_name}'].data.buildVariants.values[?@.id=='{variant_id}'].genericBuilder.slots", full_script_data_json
        )[0]
    else:
        items = jsonpath.findall(f"$..['{root_document_name}'].data.buildVariants.values[0].genericBuilder.slots", full_script_data_json)[0]
        variant_id = jsonpath.findall(f"$..['{root_document_name}'].data.buildVariants.values[0].id", full_script_data_json)[0]

    variant_name = jsonpath.findall(f"..['NgfDocumentCmWidgetContentVariantsV1DataChildVariant:{variant_id}'].title", full_script_data_json)
    if variant_name:
        build_name = f"{build_name} {variant_name[0]}"

    if not items:
        LOGGER.error(msg := "No items found")
        raise MobalyticsException(msg)
    finished_filters = []
    unique_filters = []
    aspect_upgrade_filters = []
    for item in items:
        item_filter = ItemFilterModel()
        entity_type = jsonpath.findall(".gameEntity.type", item)[0]
        if entity_type not in ["aspects", "uniqueItems"]:
            continue
        is_unique = entity_type == "uniqueItems"
        if not (item_name := str(jsonpath.findall(".gameEntity.entity.name", item)[0])):
            LOGGER.error(msg := "No item name found")
            raise MobalyticsException(msg)
        if not (slot_type := str(jsonpath.findall(".gameSlotSlug", item)[0])):
            LOGGER.error(msg := "No slot type found")
            raise MobalyticsException(msg)
        if not is_unique:
            legendary_aspect = _get_legendary_aspect(item_name)
            if legendary_aspect:
                aspect_upgrade_filters.append(legendary_aspect)
        raw_affixes = jsonpath.findall(".gameEntity.modifiers.gearStats[*].__ref", item)
        raw_inherents = jsonpath.findall(".gameEntity.modifiers.implicitStats[*].__ref", item)
        if is_unique and not raw_affixes:
            LOGGER.warning(f"Unique {item_name} had no affixes listed for it, only the aspect will be imported.")
        elif not raw_affixes and not raw_inherents:
            LOGGER.debug(f"Skipping {slot_type} because it had no stats provided.")
            continue

        item_type = None
        # Item type is hidden in the inherents. If it's in there, then we assume there are no further inherents
        is_weapon = "weapon" in slot_type
        for inherent in raw_inherents:
            affix_name = str(inherent).split(":")[1]
            potential_item_type = " ".join(affix_name.split("-")[:2]).lower()
            if is_weapon and (x := fix_weapon_type(input_str=potential_item_type)) is not None:
                item_type = x
                break
            if "offhand" in slot_type and (x := fix_offhand_type(input_str=affix_name.replace("-", " "), class_str=class_name)) is not None:
                item_type = x
                break
        if item_type:
            raw_inherents.clear()

        # Druid and sorc have a default offhand item type that we may have missed if there were no inherents
        if not item_type:
            item_type = fix_offhand_type("", class_name)

        item_type = match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot_type)) if item_type is None else item_type
        if item_type is None:
            if is_weapon:
                LOGGER.warning(f"Couldn't find an item_type for weapon slot {slot_type}, defaulting to all weapon types instead.")
                item_filter.itemType = WEAPON_TYPES
            else:
                item_filter.itemType = []
                LOGGER.warning(f"Couldn't match item_type: {slot_type}. Please edit manually")
        else:
            item_filter.itemType = [item_type]

        affixes = _convert_raw_to_affixes(raw_affixes)
        inherents = _convert_raw_to_affixes(raw_inherents)

        if is_unique:
            unique_model = UniqueModel()
            try:
                unique_model.aspect = AspectUniqueFilterModel(name=item_name)
                if affixes:
                    unique_model.affix = [AffixFilterModel(name=x.name) for x in affixes]
                unique_filters.append(unique_model)
            except Exception:
                LOGGER.exception(f"Unexpected error importing unique {item_name}, please report a bug.")
            continue

        item_filter.affixPool = [
            AffixFilterCountModel(
                count=[AffixFilterModel(name=x.name) for x in affixes],
                minCount=2,
                minGreaterAffixCount=0,
            )
        ]
        item_filter.minPower = 100
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

    if config.custom_file_name:
        build_name = config.custom_file_name

    corrected_file_name = save_as_profile(file_name=build_name, profile=profile, url=url)

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


def _get_legendary_aspect(name: str) -> str:
    if "aspect" in name.lower():
        aspect_name = correct_name(name.lower().replace("aspect", "").strip())

        if aspect_name not in Dataloader().aspect_list:
            LOGGER.warning(f"Legendary aspect '{aspect_name}' that is not in our aspect data, unable to add to AspectUpgrades.")
        else:
            return aspect_name
    return ""


def _convert_raw_to_affixes(raw_stats: list[str]) -> list[Affix]:
    result = []
    for stat in raw_stats:
        affix_name = stat.split(":")[1].replace("-", "_")
        affix_obj = Affix(name=closest_match(clean_str(_corrections(input_str=affix_name)), Dataloader().affix_dict))
        if affix_obj.name is None:
            LOGGER.error(f"Couldn't match {affix_name=}")
            continue
        result.append(affix_obj)
    return result


if __name__ == "__main__":
    src.logger.setup()
    URLS = [
        # No frills and no uniques
        "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb",
        # Is a variant of the one above
        "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb?ws-ngf5-1=activeVariantId%2C7a9c6d51-18e9-4090-a804-7b73ff00879d",
        # A standard build with uniques
        "https://mobalytics.gg/diablo-4/builds/necromancer-skeletal-warrior-minions",
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
        config = ImportConfig(X, True, True, False, None)
        import_mobalytics(config)
