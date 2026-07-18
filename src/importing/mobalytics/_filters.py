"""Convert one Mobalytics variant's slots to normalized profile filters."""

import re
from typing import TYPE_CHECKING

import jsonpath

from src.importing._conversion import as_string_keyed_mapping_list as _as_mapping_list
from src.importing._conversion import as_text as _as_text
from src.importing._filters import (
    create_item_affix_pool,
    create_seal_charm_filter,
    fix_offhand_type,
    fix_weapon_type,
    match_to_enum,
    update_mingreateraffixcount,
    weapon_slot_name_hint,
)
from src.importing.paragon import extract_mobalytics_paragon_steps
from src.importing.pipeline import Variant
from src.item import WEAPON_TYPES, Dataloader, ItemType
from src.perception import correct_name
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    AspectUniqueFilterModel,
    CharmFilterModel,
    ItemFilterModel,
    SealFilterModel,
)

from ._extraction import (
    LOGGER,
    _convert_raw_to_affixes,
    _extract_mobalytics_charm_set_name,
    _first_jsonpath_result,
    _get_legendary_aspect,
    _get_weapon_type_from_slot_tooltip,
    _humanize_mobalytics_slot,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing.config import ImportConfig


def build_variant(
    *,
    items: Sequence[Mapping[str, object]],
    class_name: str,
    config: ImportConfig,
    driver: WebDriver,
    variant_name: str,
    build_name: str,
    paragon_data: Mapping[str, object],
    error_type: type[Exception],
) -> Variant:
    finished_filters: list[ItemFilterModel] = []
    finished_filter_name_hints: list[str | None] = []
    charm_filters: list[CharmFilterModel] = []
    seal_filters: list[SealFilterModel] = []
    aspect_upgrade_filters: list[str] = []
    guessed_set_name = None
    for item in sorted(
        items, key=lambda value: _as_text(_first_jsonpath_result(".gameEntity.type", value)) != "charms"
    ):
        item_filter = ItemFilterModel()
        entity_type = _as_text(_first_jsonpath_result(".gameEntity.type", item))
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
            msg = f"No slot type found for {item_name}"
            raise error_type(msg)
        raw_affixes = _as_mapping_list(
            jsonpath.findall(".gameEntity.modifiers.gearStats[*]", item)
            + jsonpath.findall(".gameEntity.modifiers.sealStats[*]", item)
            + jsonpath.findall(".gameEntity.modifiers.charmStats[*]", item)
        )
        raw_inherents = _as_mapping_list(jsonpath.findall(".gameEntity.modifiers.implicitStats[*]", item))
        is_unique = entity_type == "uniqueItems"
        if is_unique:
            try:
                item_filter.unique_aspect = [AspectUniqueFilterModel(name=item_name)]
            except ValueError:
                LOGGER.exception(f"Unexpected error adding unique aspect for {item_name}, please report a bug.")
        if legendary_aspect := _get_legendary_aspect(item_name):
            aspect_upgrade_filters.append(legendary_aspect)
        if (
            entity_type not in ["charms", "seals"]
            and not raw_affixes
            and not raw_inherents
            and not item_filter.unique_aspect
        ):
            LOGGER.warning(f"Skipping {slot_type} because it had no stats provided.")
            continue
        item_type = _resolve_item_type(raw_inherents, slot_type, class_name)
        if item_type:
            raw_inherents.clear()
        if "seal" in slot_type.lower():
            item_type = ItemType.HoradricSeal
        elif "charm" in slot_type.lower():
            item_type = ItemType.Charm
        elif item_type is None:
            item_type = match_to_enum(enum_class=ItemType, target_string=re.sub(r"\d+", "", slot_type))
        if item_type is None and "weapon" in slot_type:
            item_type = _get_weapon_type_from_slot_tooltip(driver=driver, slot_type=slot_type)
        item_filter.item_type = (
            WEAPON_TYPES if item_type is None and "weapon" in slot_type else [item_type] if item_type else []
        )
        if item_type is None and "weapon" in slot_type:
            LOGGER.warning(
                f"Couldn't find an item_type for weapon slot {slot_type}, defaulting to all weapon types instead."
            )
        elif item_type is None:
            LOGGER.warning(f"Couldn't match item_type: {slot_type}. Please edit manually")
        affixes = _convert_raw_to_affixes(
            raw_affixes, config.import_greater_affixes, item_type, guessed_set_name=guessed_set_name
        )
        inherents = _convert_raw_to_affixes(raw_inherents, item_type=item_type, guessed_set_name=guessed_set_name)
        if item_type in [ItemType.HoradricSeal, ItemType.Charm]:
            unique_name = (
                correct_name(item_name) if correct_name(item_name) in Dataloader().aspect_unique_dict else None
            )
            set_name = _extract_mobalytics_charm_set_name(item) if item_type == ItemType.Charm else None
            if not affixes and not unique_name and not set_name:
                LOGGER.warning(f"Skipping {item_name} because it had no supported affixes, unique aspect, or set name.")
                continue
            filter_model = create_seal_charm_filter(
                affixes=affixes,
                require_gas=config.require_greater_affixes,
                model_type=CharmFilterModel if item_type == ItemType.Charm else SealFilterModel,
                unique_name=unique_name,
                set_name=set_name,
            )
            if item_type == ItemType.Charm:
                charm_filters.append(filter_model)
                if not guessed_set_name and filter_model.set:
                    guessed_set_name = filter_model.set[0]
            else:
                seal_filters.append(filter_model)
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
    return Variant(
        name=variant_name,
        affix_filters=finished_filters,
        affix_filter_name_hints=finished_filter_name_hints,
        charm_filters=charm_filters,
        seal_filters=seal_filters,
        aspect_upgrade_filters=aspect_upgrade_filters,
        paragon_steps=extract_mobalytics_paragon_steps(dict(paragon_data)),
        paragon_build_name=build_name,
    )


def _resolve_item_type(
    raw_inherents: Sequence[Mapping[str, object]], slot_type: str, class_name: str
) -> ItemType | None:
    is_weapon = "weapon" in slot_type
    for inherent in raw_inherents:
        inherent_id = str(inherent.get("id", ""))
        potential_item_type = " ".join(inherent_id.split("-")[:2]).lower()
        if is_weapon and (item_type := fix_weapon_type(input_str=potential_item_type)) is not None:
            return item_type
        if (
            "offhand" in slot_type
            and (item_type := fix_offhand_type(input_str=inherent_id.replace("-", " "), class_str=class_name))
            is not None
        ):
            return item_type
    if "offhand" in slot_type:
        return fix_offhand_type("", class_name)
    return None
