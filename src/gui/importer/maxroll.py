import json
import logging
import re
from typing import TYPE_CHECKING

import lxml.html

import src.logger
from src.config.profile_models import AspectUniqueFilterModel, CharmFilterModel, ItemFilterModel, SealFilterModel
from src.dataloader import Dataloader
from src.gui.importer.gui_common import (
    affix_dict_for_item_type,
    create_item_affix_pool,
    create_seal_charm_filter,
    fix_offhand_type,
    fix_weapon_type,
    get_with_retry,
    is_unique_like_rarity,
    match_to_enum,
    retry_importer,
    update_mingreateraffixcount,
)
from src.gui.importer.gui_common import as_string_keyed_mapping as _as_mapping
from src.gui.importer.gui_common import as_string_keyed_mapping_list as _as_mapping_list
from src.gui.importer.gui_common import as_text as _as_text
from src.gui.importer.import_pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter, Variant
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.paragon_export import extract_maxroll_paragon_steps
from src.item.data.affix import Affix, AffixType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.text import clean_str, closest_match
from src.scripts import correct_name

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True

BUILD_GUIDE_BASE_URL = "https://maxroll.gg/d4/build-guides/"
BUILD_SCRIPT_PREFIX = "window.__remixContext = "
PLANNER_API_BASE_URL = "https://planners.maxroll.gg/profiles/d4/"
PLANNER_API_DATA_URL = "https://assets-ng.maxroll.gg/d4-tools/game/data.min.json?39e88625"
PLANNER_API_REGEX = re.compile(r'(https://maxroll\.gg/d4/planner/[^"|\\]*)')
PLANNER_BASE_URL = "https://maxroll.gg/d4/planner/"
SCRIPT_XPATH = "//div[@id='root']/script"
SKILL_RANK_AFFIX_KEY_REGEX = re.compile(r"(?:_Category_|_Special_)(?P<label>[A-Za-z0-9]+)")
SKILL_RANK_BONUS_FORMULAS = {"GearAffix_SkillRankBonus", "GearAffix_SkillRankBonus_1to2"}
SKILL_RANK_DESC_LABEL_REGEX = re.compile(r"\{c_important\}([^{}]+)\{/c\}\s+Skills")


class MaxrollError(Exception):
    pass


@retry_importer
def import_maxroll(config: ImportConfig):
    url = config.url.strip().replace("\n", "")
    if PLANNER_BASE_URL not in url and BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a maxroll build guide or maxroll planner url")
        return
    LOGGER.info(f"Loading {url}")
    if BUILD_GUIDE_BASE_URL in url:
        api_url, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_guide(url)
    else:
        api_url, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_planner(url)
    try:
        r = get_with_retry(url=api_url)
    except ConnectionError:
        LOGGER.error("Couldn't get planner")
        return
    all_data = r.json()
    guide_season = all_data.get("season", "")
    build_data = json.loads(all_data["data"])
    if build_id_is_visible_position:
        build_id = _resolve_visible_profile_index(build_data["profiles"], build_id)
    items = build_data["items"]
    try:
        mapping_data = get_with_retry(url=PLANNER_API_DATA_URL).json()
    except ConnectionError:
        LOGGER.error("Couldn't get planner data")
        return
    # The attribute descriptions are not always consistent with the casing for the key so we fix that here
    mapping_data["attributeDescriptions"] = {k.lower(): v for k, v in mapping_data["attributeDescriptions"].items()}
    active_profile = build_data["profiles"][build_id]
    build_header = all_data["name"] or all_data["class"]
    variant_name = active_profile["name"] or ""
    build_name = build_header
    if not build_name:
        build_name = all_data["class"]
    if variant_name:
        build_name += f"_{variant_name}"
    finished_filters: list[ItemFilterModel] = []
    charm_filters: list[CharmFilterModel] = []
    seal_filters: list[SealFilterModel] = []
    aspect_upgrade_filters: list[str] = []
    for item_id in active_profile["items"].values():
        resolved_item = items[str(item_id)]
        resolved_item_id = resolved_item["id"]
        item_name = mapping_data["items"][resolved_item_id]["name"]
        rarity = _find_item_rarity(resolved_item_id, mapping_data)
        is_unique_like = is_unique_like_rarity(rarity)

        item_filter = ItemFilterModel()
        if (
            item_type := _find_item_type(
                mapping_data=mapping_data["items"], value=resolved_item["id"], class_name=all_data["class"]
            )
        ) is None:
            LOGGER.warning(
                f"Couldn't find item type for {resolved_item['id']} from mapping data provided by Maxroll. Skipping item."
            )
            continue

        # TODO I don't think this code needs to be siloed, I think it can be mostly part of the normal flow so we're not repeating work. It'd just require some refactoring
        if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
            if "explicits" not in resolved_item:
                LOGGER.warning(
                    f"Maxroll is providing unreliable data for Seals/Charms, skipping a {item_type.value} for this build."
                )
                continue
            seal_charm_affixes = _find_item_affixes(
                mapping_data=mapping_data,
                item_affixes=resolved_item["explicits"],
                item_type=item_type,
                import_greater_affixes=config.import_greater_affixes,
            )
            # Extract unique aspect and set info for charms
            charm_or_seal_unique_aspect = None
            charm_set_name = None
            if is_unique_like:
                charm_or_seal_unique_aspect = correct_name(_unique_name_special_handling(item_name))
            elif rarity == ItemRarity.Set:
                set_key = mapping_data["items"][resolved_item_id]["set"]
                charm_set_name = correct_name(mapping_data["itemSets"][set_key]["name"])
            if not seal_charm_affixes and not charm_or_seal_unique_aspect and not charm_set_name:
                LOGGER.warning(
                    f"Skipping {resolved_item.get('name', '(could not determine item name)')} because it had no supported affixes, unique aspect, or set name."
                )
                continue
            if item_type == ItemType.Charm:
                charm_filters.append(
                    create_seal_charm_filter(
                        affixes=seal_charm_affixes,
                        require_gas=config.require_greater_affixes,
                        model_type=CharmFilterModel,
                        unique_name=charm_or_seal_unique_aspect,
                        set_name=charm_set_name,
                    )
                )
            else:
                seal_filters.append(
                    create_seal_charm_filter(
                        affixes=seal_charm_affixes,
                        require_gas=config.require_greater_affixes,
                        model_type=SealFilterModel,
                        unique_name=charm_or_seal_unique_aspect,
                        set_name=charm_set_name,
                    )
                )
            continue

        item_filter.item_type = [item_type]

        # Legendary aspect upgrade handling
        if rarity == ItemRarity.Legendary and config.import_aspect_upgrades:
            legendary_aspect = _find_legendary_aspect(
                mapping_data, resolved_item.get("legendaryPower", resolved_item.get("aspects", {}))
            )
            if legendary_aspect:
                if legendary_aspect not in Dataloader().aspect_list:
                    LOGGER.warning(
                        f"Found legendary aspect '{legendary_aspect}' that is not in our aspect data, unable to add "
                        f"to AspectUpgrades. Please report a bug."
                    )
                else:
                    aspect_upgrade_filters.append(legendary_aspect)

        # Unique aspect, if the item is a unique or a mythic (mythics are functionally uniques, just purple)
        if is_unique_like:
            unique_name = item_name
            try:
                unique_name = _unique_name_special_handling(unique_name)
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=unique_name)]
            except Exception:
                LOGGER.exception(f"Unexpected error adding unique aspect for {unique_name}, please report a bug.")

        # Standard item handling
        affixes = _find_item_affixes(
            mapping_data=mapping_data,
            item_affixes=resolved_item["explicits"],
            item_type=item_type,
            import_greater_affixes=config.import_greater_affixes,
        )
        if affixes:
            item_filter.affix_pool = create_item_affix_pool(affixes=affixes, unique_like=is_unique_like)
            update_mingreateraffixcount(item_filter, config.require_greater_affixes)
        elif not item_filter.unique_aspect:
            LOGGER.warning(f"Skipping {item_name} because it had no supported affixes or unique aspect.")
            continue

        item_filter.min_power = 100
        # Match the other guide importers: let the shared pipeline deduplicate identical affix filters
        # instead of preserving duplicates via incrementing name suffixes.
        finished_filters.append(item_filter)

    ImportPipeline.run(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="maxroll",
                class_name=all_data["class"],
                build_header=build_header,
                season_number=guide_season,
                variants=[
                    Variant(
                        name=variant_name,
                        affix_filters=finished_filters,
                        charm_filters=charm_filters,
                        seal_filters=seal_filters,
                        aspect_upgrade_filters=aspect_upgrade_filters,
                        paragon_steps=extract_maxroll_paragon_steps(active_profile, mapping_data),
                        paragon_build_name=build_name,
                    )
                ],
            ),
        ),
        config=config,
    )


def _attribute_description_corrections(input_str: str) -> str:
    match input_str:
        case "On_Hit_Vulnerable_Proc_Chance":
            return "On_Hit_Vulnerable_Proc".lower()
        case "Movement_Bonus_On_Elite_Kill":
            return "Movement_Speed_Bonus_On_Elite_Kill".lower()
    return input_str.lower()


def _find_item_rarity(resolved_item_id, mapping_data) -> ItemRarity:
    # magic/rare = 0, legendary = 1, unique = 2, set = 3, mythic = 4
    if resolved_item_id in mapping_data["items"]:
        rarity_id = mapping_data["items"][resolved_item_id]["magicType"]
        if rarity_id == 1:
            return ItemRarity.Legendary
        if rarity_id == 2:
            return ItemRarity.Unique
        if rarity_id == 3:
            return ItemRarity.Set
        if rarity_id == 4:
            return ItemRarity.Mythic

    return ItemRarity.Common


def _find_item_affixes(
    mapping_data: Mapping[str, object],
    item_affixes: Sequence[Mapping[str, object]],
    item_type: ItemType,
    import_greater_affixes: bool = False,
) -> list[Affix]:
    res = []
    affix_data = _as_mapping(mapping_data.get("affixes"))
    ui_strings = _as_mapping(mapping_data.get("uiStrings"))
    damage_type_labels = _as_text_mapping(ui_strings.get("damageType"))
    resource_type_labels = _as_text_mapping(ui_strings.get("resourceType"))
    attributes = _as_mapping(mapping_data.get("attributes"))
    attribute_descriptions = _as_text_mapping(mapping_data.get("attributeDescriptions"))
    skills = _as_mapping(mapping_data.get("skills"))
    for affix_id in item_affixes:
        affix_reference = _as_mapping(affix_id)
        reference_id = affix_reference.get("nid")
        for affix_key, raw_affix in affix_data.items():
            affix = _as_mapping(raw_affix)
            affix_value = affix.get("id")
            if affix_value != reference_id or not isinstance(affix_value, (int, str)):
                continue
            if affix.get("magicType") in [2, 4]:
                break
            attributes_list = _as_mapping_list(affix.get("attributes"))
            attr_desc = _attr_desc_special_handling(affix_value)
            if not attr_desc:
                if not attributes_list:
                    continue
                attribute = attributes_list[0]
                formula = attribute.get("formula")
                if isinstance(formula, str) and formula.startswith("SancAffix_"):
                    LOGGER.info(f"Skipping Transfiguration affix for item type '{item_type.value}'")
                    break
                if formula in [
                    "GearAffix_Resource_Per_Second",
                    "GearAffix_DamageType",
                    "GearAffix_DamageType_Greater",
                    "GearAffix_Resource_On_Kill",
                    "GearAffix_Resource_On_Kill_Warlock",
                    "GearAffix_Resistance_Single",
                ]:
                    if formula in ["GearAffix_DamageType", "GearAffix_DamageType_Greater"]:
                        param = str(attribute["param"])
                        if param in damage_type_labels:
                            attr_desc = damage_type_labels[param] + " Damage Multiplier"
                        elif "desc" in affix:
                            # These are seal affixes and we have to get the skill from the description
                            pattern = r"\{c_important\}([^{}]+)\{/c\}\s*(.+)$"
                            match = re.search(pattern, _as_text(affix.get("desc")))
                            if match:
                                attr_desc = f"{match.group(1)} {match.group(2)}"
                    elif formula == "GearAffix_Resistance_Single":
                        attr_desc = damage_type_labels[str(attribute["param"])] + " Resistance"
                    elif formula == "GearAffix_Resource_Per_Second":
                        param = str(attribute["param"])
                        attr_desc = resource_type_labels[param] + " Regeneration"
                    elif formula in ["GearAffix_Resource_On_Kill", "GearAffix_Resource_On_Kill_Warlock"]:
                        attr_desc = resource_type_labels[str(attribute["param"])] + " On Kill"
                elif "param" not in attribute:
                    attr_id = attribute["id"]
                    attr_obj = _as_mapping(attributes.get(str(attr_id)))
                    attr_name = _as_text(attr_obj.get("name"))
                    attr_desc = attribute_descriptions.get(_attribute_description_corrections(attr_name))
                    if not attr_desc:
                        LOGGER.warning(
                            f"Unable to map {attr_name} from MaxRoll data to an affix, skipping affix and please report a bug."
                        )
                        continue
                else:  # must be + to talent or skill
                    attr_param = attribute["param"]
                    for raw_skill in skills.values():
                        skill_data = _as_mapping(raw_skill)
                        if skill_data.get("id") == attr_param:
                            attr_desc = f"to {_as_text(skill_data.get('name'))}"
                            break
                    else:
                        attr_desc = _find_skill_rank_affix_description(
                            mapping_data=mapping_data, affix_key=affix_key, attribute=attribute
                        )

                # Below is handling for seal affixes tied to a set. We attach the set to the front.
                # If this ends up not working for some reason, a second option is to take the key
                # like "Talisman_SealAffix_Set_Barbarian_05_AncientSkillRankBonus" and convert it to
                # "Talisman_Barbarian_05" and then find that in the mapping data. That will also give set name.
                if "Talisman" in affix_key and "Set" in affix_key:
                    pattern = r"\{c_set\}([^{}]+)\{/c\}"
                    match = re.search(pattern, _as_text(affix.get("desc"))) if "desc" in affix else None
                    if match:
                        attr_desc = match.group(1) + " " + attr_desc
                    else:
                        LOGGER.warning(
                            f"We thought affix {attr_desc} was a seal-based affix activated by a set but we could not determine the set. The affix is skipped, please report a bug with a link to the build."
                        )
                        continue

            clean_desc = re.sub(r"\[.*?\]|[^a-zA-Z ]", "", attr_desc)
            clean_desc = clean_desc.replace("SecondSeconds", "seconds")
            if not clean_desc:
                LOGGER.warning(
                    f"We were unable to map an attribute on item type {item_type.value} to an affix. Please report a bug and include a link to the build, we are skipping that affix."
                )
                continue

            affix_dict = affix_dict_for_item_type(item_type=item_type)
            affix_obj = Affix(name=closest_match(clean_str(clean_desc), affix_dict))
            if import_greater_affixes and affix_id.get("greater") is True:
                affix_obj.type = AffixType.greater
            if affix_obj.name is not None:
                res.append(affix_obj)
            elif (
                attributes_list
                and "formula" in attributes_list[0]
                and attributes_list[0]["formula"] == "InherentAffixAnyResist_Ring"
            ):
                LOGGER.info("Skipping InherentAffixAnyResist_Ring")
            else:
                LOGGER.error(f"Couldn't match {affix_id=}")
            break
    return res


def _find_skill_rank_affix_description(
    mapping_data: Mapping[str, object], affix_key: str, attribute: Mapping[str, object]
) -> str:
    if attribute.get("formula") not in SKILL_RANK_BONUS_FORMULAS:
        return ""

    param = attribute.get("param")
    param_int = param if isinstance(param, int) and not isinstance(param, bool) else None
    if (label := _find_skill_rank_label_from_descriptions(mapping_data, param_int)) or (
        label := _find_skill_rank_label_from_affix_key(affix_key)
    ):
        return f"to {label} skills"
    return ""


def _find_skill_rank_label_from_descriptions(mapping_data: Mapping[str, object], param: int | None) -> str:
    if param is None:
        return ""

    for raw_affix in _as_mapping(mapping_data.get("affixes")).values():
        affix = _as_mapping(raw_affix)
        if not any(
            attr.get("formula") in SKILL_RANK_BONUS_FORMULAS and attr.get("param") == param
            for attr in _as_mapping_list(affix.get("attributes"))
        ):
            continue
        if match := SKILL_RANK_DESC_LABEL_REGEX.search(_as_text(affix.get("desc"))):
            return match.group(1)
    return ""


def _find_skill_rank_label_from_affix_key(affix_key: str) -> str:
    if "SkillRankBonus_AllSkills" in affix_key:
        return "all"
    if match := SKILL_RANK_AFFIX_KEY_REGEX.search(affix_key):
        label = match.group("label")
        if label == "Bludgeoning":
            return "combat"
        label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", label)
        label = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", label)
        return " ".join(label.split())
    return ""


def _find_legendary_aspect(
    mapping_data: Mapping[str, object], legendary_aspect: Mapping[str, object] | list[object]
) -> str | None:
    if not legendary_aspect:
        return None

    if isinstance(legendary_aspect, list):
        if not legendary_aspect:
            return None
        first_aspect = legendary_aspect[0]
        if not isinstance(first_aspect, dict):
            return None
        aspect_data = _as_mapping(first_aspect)
    else:
        aspect_data = _as_mapping(legendary_aspect)

    aspect_id = aspect_data.get("nid")
    for raw_affix in _as_mapping(mapping_data.get("affixes")).values():
        affix = _as_mapping(raw_affix)
        if affix.get("id") != aspect_id:
            continue

        prefix = affix.get("prefix")
        if isinstance(prefix, str):
            return correct_name(prefix)
        suffix = affix.get("suffix")
        if isinstance(suffix, str):
            return correct_name(suffix)
        return None

    return None


def _attr_desc_special_handling(affix_id: int | str) -> str:
    match affix_id:
        case 2609197:
            return "charm slot"
        # case 1014505 | 2051010:
        #     return "evade grants movement speed for second"
        # case 2568489:
        #     return "hunger increased reputation from kill streaks"
        # case 2568491:
        #     return "hunger increased experience from kill streaks"
        # case 2057810:
        #     return "damage reduction from bleeding enemies"
        # case 2067844:
        #     return "maximum poison resistance"
        # case 2037914:
        #     return "subterfuge cooldown reduction"
        # case 2123788:
        #     return "chance for core skills to hit twice"
        # case 2119054:
        #     return "chance for basic skills to deal double damage"
        # case 2119058:
        #     return "basic lucky hit chance"
        # case 2052125:
        #     return "non-physical damage"
        case _:
            return ""


def _unique_name_special_handling(unique_name: str) -> str:
    match unique_name:
        case "[PH] Season 7 Necro Pants":
            return "kessimes_legacy"
        case "[PH] Season 7 Barb Chest":
            return "mantle_of_mountains_fury"
        case _:
            return unique_name.replace("\xa0", " ")


def _find_item_type(mapping_data: Mapping[str, Mapping[str, str]], value: str, class_name: str = "") -> ItemType | None:
    for d_key, d_value in mapping_data.items():
        if d_key == value:
            item_type_str = d_value["type"]
            normalized_item_type_str = _normalize_item_type_str_for_import_helpers(item_type_str)
            if (item_type := fix_weapon_type(input_str=normalized_item_type_str)) is not None:
                return item_type
            if (
                any(substring in normalized_item_type_str for substring in ["focus", "off hand", "shield", "totem"])
            ) and (item_type := fix_offhand_type(input_str=normalized_item_type_str, class_str=class_name)) is not None:
                return item_type
            if (res := match_to_enum(enum_class=ItemType, target_string=item_type_str, check_keys=True)) is None:
                LOGGER.error("Couldn't match item type to enum")
                return None
            return res
    return None


def _normalize_item_type_str_for_import_helpers(item_type_str: str) -> str:
    normalized_item_type = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", item_type_str)
    normalized_item_type = re.sub(r"(?<=[A-Za-z])(?=[12]H\b)", " ", normalized_item_type)
    normalized_item_type = normalized_item_type.replace("-", " ").lower()
    normalized_item_type = " ".join(normalized_item_type.split())
    return re.sub(r"\b([a-z]+)\s+(1h|2h)\b", r"\2 \1", normalized_item_type)


def _extract_planner_url_and_id_from_planner(url: str) -> tuple[str, int, bool]:
    planner_suffix = url.split(PLANNER_BASE_URL)
    if len(planner_suffix) != 2:
        LOGGER.error(msg := "Invalid planner url")
        raise MaxrollError(msg)
    if "#" in planner_suffix[1]:
        planner_id, data_id = planner_suffix[1].split("#")
        data_id = int(data_id) - 1
        build_id_is_visible_position = True
    else:
        planner_id = planner_suffix[1]

        try:
            r = get_with_retry(url=PLANNER_API_BASE_URL + planner_id)
        except ConnectionError as exc:
            LOGGER.exception(msg := "Couldn't get planner")
            raise MaxrollError(msg) from exc
        data_id = json.loads(r.json()["data"])["activeProfile"]
        build_id_is_visible_position = False
    return PLANNER_API_BASE_URL + planner_id, data_id, build_id_is_visible_position


def _extract_planner_url_and_id_from_guide(url: str) -> tuple[str, int, bool]:
    """Resolve a build guide to the underlying planner API url and profile selection."""
    try:
        r = get_with_retry(url=url)
    except ConnectionError as exc:
        LOGGER.exception(msg := "Couldn't get build guide")
        raise MaxrollError(msg) from exc
    data = lxml.html.fromstring(r.text)
    # As of season 13, the link to the planner is stuck in a script so we get it from there
    script_elements = data.xpath(SCRIPT_XPATH)
    for script_element in script_elements:
        if script_element.text and script_element.text.strip().startswith(BUILD_SCRIPT_PREFIX):
            planner_match = PLANNER_API_REGEX.search(script_element.text)
            if planner_match is None:
                continue
            planner_link = planner_match.group()
            if planner_link:
                api_url, build_id, build_id_is_visible_position = _extract_planner_url_and_id_from_planner(planner_link)
                return api_url, build_id, build_id_is_visible_position

    msg = "Couldn't resolve a planner profile from this Maxroll build guide. Use the planner link directly and please report a bug."
    LOGGER.error(msg)
    raise MaxrollError(msg)


def _resolve_visible_profile_index(profiles: Sequence[Mapping[str, object]], visible_profile_index: int) -> int:
    visible_index = 0
    for profile_index, profile in enumerate(profiles):
        if profile.get("hidden"):
            continue
        if visible_index == visible_profile_index:
            return profile_index
        visible_index += 1
    return visible_profile_index


def _as_text_mapping(value: object) -> Mapping[str, str]:
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str) and isinstance(item, str)}


def _extract_guide_profile_id(embed: lxml.html.HtmlElement) -> int | None:
    if data_id := embed.get("data-d4-id"):
        return int(data_id.split(",")[0]) - 1
    if data_ids := embed.get("data-d4-data"):
        guide_profile_ids = [int(value) for value in data_ids.split(",") if value]
        if (active_tab_index := _extract_active_guide_embed_tab_index(embed)) is not None and active_tab_index < len(
            guide_profile_ids
        ):
            return guide_profile_ids[active_tab_index] - 1
        return guide_profile_ids[0] - 1
    return None


def _extract_active_guide_embed_tab_index(embed: lxml.html.HtmlElement) -> int | None:
    for index, tab in enumerate(embed.xpath(".//*[contains(@class, 'd4t-tabs')]/li")):
        if "d4t-active" in (tab.get("class") or ""):
            return index
    return None


if __name__ == "__main__":
    src.logger.setup()
    URLS = ["https://maxroll.gg/d4/planner/y4aa0i0w#3"]
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
        import_maxroll(config)
