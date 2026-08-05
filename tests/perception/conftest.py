import json
from pathlib import Path
from typing import cast

import pytest

from src.game_data import ItemRarity, ItemType
from src.item import Affix, AffixType, Aspect, Item, SeasonalAttribute


def _enum_value(enum_type, value):
    return None if value is None else enum_type(value)


def _loc(value: object) -> tuple[int, int] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    return cast("int", value[0]), cast("int", value[1])


def _affix(data: object) -> Affix:
    values = cast("dict[str, object]", data)
    return Affix(
        loc=_loc(values["loc"]),
        max_value=cast("float | None", values["max_value"]),
        min_value=cast("float | None", values["min_value"]),
        name=cast("str", values["name"]),
        text=cast("str", values["text"]),
        type=AffixType(cast("int", values["type"])),
        value=cast("float | None", values["value"]),
    )


def _item(data: object) -> Item:
    values = cast("dict[str, object]", data)
    aspect_data = values["aspect"]
    aspect = None
    if aspect_data:
        aspect_values = cast("dict[str, object]", aspect_data)
        aspect = Aspect(
            name=cast("str", aspect_values["name"]),
            loc=_loc(aspect_values["loc"]),
            min_value=cast("float | None", aspect_values["min_value"]),
            max_value=cast("float | None", aspect_values["max_value"]),
            text=cast("str", aspect_values["text"]),
            value=cast("float | None", aspect_values["value"]),
        )
    return Item(
        affixes=[_affix(affix) for affix in cast("list[object]", values["affixes"])],
        aspect=aspect,
        codex_upgrade=cast("bool", values["codex_upgrade"]),
        cosmetic_upgrade=cast("bool", values["cosmetic_upgrade"]),
        inherent=[_affix(affix) for affix in cast("list[object]", values["inherent"])],
        is_ancestral=cast("bool", values["is_ancestral"]),
        is_in_shop=cast("bool", values["is_in_shop"]),
        item_type=_enum_value(ItemType, cast("str | None", values["item_type"])),
        name=cast("str | None", values["name"]),
        original_name=cast("str | None", values["original_name"]),
        power=cast("int | None", values["power"]),
        rarity=_enum_value(ItemRarity, cast("str | None", values["rarity"])),
        seasonal_attribute=_enum_value(SeasonalAttribute, cast("str | None", values["seasonal_attribute"])),
        set=cast("str | None", values["set"]),
    )


@pytest.fixture
def parser_cases() -> list[tuple[list[str], Item]]:
    data_dir = Path(__file__).parent / "data"
    cases = []
    for path in sorted(data_dir.glob("parser_*.json")):
        cases.extend(json.loads(path.read_text(encoding="utf-8")))
    return [(case["input"], _item(case["expected"])) for case in cases]
