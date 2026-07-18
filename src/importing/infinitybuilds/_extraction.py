import json
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from src.importing._conversion import as_string_keyed_mapping as _as_object
from src.importing._filters import affix_dict_for_item_type
from src.importing._web import get_with_retry
from src.item import Affix, AffixType, ItemType
from src.perception import clean_str, closest_match, correct_name

from ._models import _ResolvedGearData

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    import lxml.html

    from ._models import (
        BuildData,
        CatalogT,
        _CatalogAffix,
        _CatalogAspect,
        _CatalogItem,
        _GearPiece,
        _RawAffix,
        _VariantData,
    )

LOGGER = logging.getLogger(__name__)
TOOLS_API_BASE_URL = "https://tools.infinitybuilds.gg/api/games/diablo4/build-data"
SCRIPT_XPATH = "//script"
NEXT_F_PUSH_REGEX = re.compile(r'^self\.__next_f\.push\(\[(?:\d+),(".*")\]\)\s*;?$', re.DOTALL)
CATALOG_ID_INSTANCE_PREFIX = re.compile(r"^(item|aspect)-\d+-")


def _extract_build_title(raw_html_data: lxml.html.HtmlElement) -> str:
    title_elems = raw_html_data.xpath("//title")
    if title_elems and title_elems[0].text:
        # Page titles look like "Build Name | InfinityBuilds"
        return title_elems[0].text.split("|")[0].strip()
    return ""


def _extract_build_data(raw_html_data: lxml.html.HtmlElement) -> BuildData | None:
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
            content_value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(content_value, str):
            continue
        content = content_value
        variants_key = '"variants":['
        key_idx = content.find(variants_key)
        if key_idx == -1:
            continue
        array_start = key_idx + len(variants_key) - 1
        try:
            variants_raw = _extract_balanced(content, array_start, "[", "]")
            variants_value = json.loads(variants_raw)
        except ValueError, json.JSONDecodeError:
            continue
        if not isinstance(variants_value, list):
            continue
        variants = [_parse_variant_data(value) for value in variants_value if isinstance(value, dict)]
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


def _canonical_catalog_id(raw_id: str | None) -> str | None:
    """Strip extra numeric value from catalog id.

    Some build variants embed gear with an extra numeric instance id spliced into the item/aspect
    which the catalog returned by the API doesn't have. Strip it before lookups.
    """
    return CATALOG_ID_INSTANCE_PREFIX.sub(r"\1-", raw_id) if raw_id else raw_id


def _resolve_gear_data(class_name: str, gear: Sequence[Mapping[str, object]]) -> _ResolvedGearData:
    normalized_gear = [_parse_gear_piece(_as_object(piece)) for piece in gear]
    item_ids = sorted({_canonical_catalog_id(g["itemId"]) for g in normalized_gear if g.get("itemId")})
    aspect_ids = sorted({_canonical_catalog_id(g["aspectId"]) for g in normalized_gear if g.get("aspectId")})
    affix_ids = sorted({
        affix["affixId"] for g in normalized_gear for affix in (g.get("affixes") or []) if affix.get("affixId")
    })
    params = {"classId": class_name, "mode": "view", "shape": "2", "locale": "en"}
    if item_ids:
        params["itemIds"] = ",".join(item_ids)
    if aspect_ids:
        params["aspectIds"] = ",".join(aspect_ids)
    if affix_ids:
        params["affixIds"] = ",".join(affix_ids)
    response = get_with_retry(f"{TOOLS_API_BASE_URL}?{urlencode(params)}")
    dataset = _as_object(_as_object(response.json()).get("dataset"))
    gear_data = _as_object(dataset.get("gear"))
    return _ResolvedGearData(
        items=_catalog_by_id(_parse_catalog_items(gear_data.get("items"))),
        aspects=_catalog_by_id(_parse_catalog_aspects(gear_data.get("aspects"))),
        affixes=_catalog_by_id(_parse_catalog_affixes(gear_data.get("affixes"))),
    )


def _normalize_aspect_name(name: str) -> str:
    # Aspect names in our data drop the word "aspect" itself (e.g. "Edgemaster's Aspect" -> "edgemasters").
    return correct_name(name.lower().replace("aspect", "").strip()) or ""


def _convert_raw_to_affixes(
    raw_affixes: Sequence[Mapping[str, object]],
    resolved_affixes: Mapping[str, Mapping[str, object]],
    import_greater_affixes: bool = False,
    item_type: ItemType | None = None,
) -> list[Affix]:
    result = []
    affix_dict = affix_dict_for_item_type(item_type=item_type)
    for raw_value in raw_affixes:
        raw_affix = _as_object(raw_value)
        if raw_affix.get("tempered"):
            continue
        affix_id = raw_affix.get("affixId")
        resolved_affix = _as_object(resolved_affixes.get(affix_id))
        if not resolved_affix or not resolved_affix.get("label"):
            LOGGER.error(f"Couldn't resolve {affix_id=}")
            continue
        label = resolved_affix.get("label")
        if not isinstance(label, str):
            continue
        stat_clean = clean_str(label)
        matched_name = closest_match(stat_clean, affix_dict)
        if matched_name is None:
            LOGGER.error(f"Couldn't match {resolved_affix['label']=}")
            continue
        affix_obj = Affix(name=matched_name)
        if import_greater_affixes and resolved_affix.get("greaterAffixEligible") is True:
            value_range = _as_object(resolved_affix.get("valueRange"))
            max_value = value_range.get("max")
            raw_roll = raw_affix.get("value", 0)
            if (
                isinstance(max_value, (int, float))
                and not isinstance(max_value, bool)
                and isinstance(raw_roll, (int, float))
                and not isinstance(raw_roll, bool)
                and raw_roll >= max_value
            ):
                affix_obj.type = AffixType.greater
        result.append(affix_obj)
    return result


def _parse_variant_data(value: dict[str, object]) -> _VariantData:
    variant: _VariantData = {}
    for key in ("id", "name"):
        item = value.get(key)
        if isinstance(item, str):
            variant[key] = item
    gear = value.get("gear")
    if isinstance(gear, list):
        variant["gear"] = [_parse_gear_piece(_as_object(piece)) for piece in gear if isinstance(piece, dict)]
    paragon = value.get("paragon")
    if isinstance(paragon, dict):
        variant["paragon"] = _as_object(paragon)
    return variant


def _parse_gear_piece(value: dict[str, object]) -> _GearPiece:
    gear_piece: _GearPiece = {}
    for key in ("kind", "itemId", "aspectId", "slot"):
        item = value.get(key)
        if isinstance(item, str):
            gear_piece[key] = item
    raw_affixes = value.get("affixes")
    if isinstance(raw_affixes, list):
        gear_piece["affixes"] = [
            _parse_raw_affix(_as_object(affix)) for affix in raw_affixes if isinstance(affix, dict)
        ]
    return gear_piece


def _parse_raw_affix(value: dict[str, object]) -> _RawAffix:
    affix: _RawAffix = {}
    affix_id = value.get("affixId")
    if isinstance(affix_id, str):
        affix["affixId"] = affix_id
    tempered = value.get("tempered")
    if isinstance(tempered, bool):
        affix["tempered"] = tempered
    swapped = value.get("swapped")
    if isinstance(swapped, bool):
        affix["swapped"] = swapped
    raw_value = value.get("value")
    if isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool):
        affix["value"] = raw_value
    return affix


def _parse_catalog_items(value: object) -> list[_CatalogItem]:
    result: list[_CatalogItem] = []
    for entry in value if isinstance(value, list) else []:
        entry_object = _as_object(entry)
        entry_id = entry_object.get("id")
        if not isinstance(entry_id, str):
            continue
        item: _CatalogItem = {"id": entry_id}
        for key in ("label", "rarity", "slot"):
            item_value = entry_object.get(key)
            if isinstance(item_value, str):
                item[key] = item_value
        result.append(item)
    return result


def _parse_catalog_aspects(value: object) -> list[_CatalogAspect]:
    result: list[_CatalogAspect] = []
    for entry in value if isinstance(value, list) else []:
        entry_object = _as_object(entry)
        entry_id = entry_object.get("id")
        if isinstance(entry_id, str):
            label = entry_object.get("label")
            result.append({"id": entry_id, "label": label if isinstance(label, str) else ""})
    return result


def _parse_catalog_affixes(value: object) -> list[_CatalogAffix]:
    result: list[_CatalogAffix] = []
    for entry in value if isinstance(value, list) else []:
        entry_object = _as_object(entry)
        entry_id = entry_object.get("id")
        if not isinstance(entry_id, str):
            continue
        label = entry_object.get("label")
        affix: _CatalogAffix = {
            "id": entry_id,
            "label": label if isinstance(label, str) else "",
            "greaterAffixEligible": entry_object.get("greaterAffixEligible") is True,
        }
        value_range = entry_object.get("valueRange")
        if isinstance(value_range, dict):
            max_value = value_range.get("max")
            if isinstance(max_value, (int, float)) and not isinstance(max_value, bool):
                affix["valueRange"] = {"max": max_value}
        result.append(affix)
    return result


def _catalog_by_id(entries: Sequence[CatalogT]) -> dict[str, CatalogT]:
    return {entry["id"]: entry for entry in entries if "id" in entry}
