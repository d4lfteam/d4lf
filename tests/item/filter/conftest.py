import importlib
import json
import typing
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import src.item.filter.engine as engine_module
import src.item.filter.equipment as equipment_module
import src.item.filter.special as special_module
from src.item import Filter

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _type(name: str) -> type:
    module, _, qualname = name.rpartition(".")
    value: object = importlib.import_module(module)
    for part in qualname.split("."):
        value = getattr(value, part)
    return cast("type", value)


def _mapping(value: object) -> dict[str, object]:
    return cast("dict[str, object]", value)


def _create_mocked_filter(mocker: MockerFixture) -> Filter:
    filter_obj = Filter()
    filter_obj.affix_filters = {}
    filter_obj.aspect_upgrade_filters = {}
    filter_obj.paragon_filters = {}
    filter_obj.global_unique_filters = {}
    filter_obj.seal_filters = {}
    filter_obj.charm_filters = {}
    filter_obj.sigil_filters = {}
    filter_obj.tribute_filters = {}
    filter_obj.files_loaded = True
    mocker.patch.object(filter_obj, "_did_files_change", return_value=False)
    return filter_obj


def _patch_override_settings(mocker, **overrides):
    general = SimpleNamespace(
        filter_equipment=True,
        filter_sigils=True,
        filter_tributes=True,
        filter_seals=True,
        filter_charms=True,
        handle_cosmetics="ignore",
        keep_aspects="upgrade",
        handle_uniques="favorite",
        ignore_escalation_sigils=True,
    )
    for key, value in overrides.items():
        setattr(general, key, value)
    settings = SimpleNamespace(general=general)
    mocker.patch.object(engine_module, "get_settings", return_value=settings)
    mocker.patch.object(equipment_module, "get_settings", return_value=settings)
    mocker.patch.object(special_module, "get_settings", return_value=settings)
    return settings


def _decode(value: object) -> object:
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    value = _mapping(value)
    if "__enum__" in value:
        return getattr(_type(cast("str", value["__enum__"])), cast("str", value["value"]))
    if "__class__" in value:
        cls = _type(cast("str", value["__class__"]))
        fields = _mapping(_decode(value["fields"]))
        try:
            return cls(**fields)
        except TypeError:
            return cls(fields)
    return {key: _decode(item) for key, item in value.items()}


with (Path(__file__).parent / "data" / "fixtures.json").open(encoding="utf-8") as fixture_file:
    _fixtures = _mapping(_decode(json.load(fixture_file)))

affixes: Any = _mapping(_fixtures["affixes"])["affixes"]
aspects: Any = _mapping(_fixtures["aspects"])["aspects"]
charms: Any = _mapping(_fixtures["charms"])["charms"]
filters: Any = type("Filters", (), _mapping(_fixtures["filters"]))()
items: Any = _mapping(_fixtures["items"])["items"]
seals: Any = _mapping(_fixtures["seals"])["seals"]
sigil_data: Any = _mapping(_fixtures["sigils"])
tributes: Any = _mapping(_fixtures["tributes"])["tributes"]
uniques: Any = _mapping(_fixtures["uniques"])

sigils = sigil_data["sigils"]
sigil_derived_legendary = sigil_data["sigil_derived_legendary"]
sigil_derived_rare = sigil_data["sigil_derived_rare"]
sigil_jalal = sigil_data["sigil_jalal"]
sigil_mythic_fallback = sigil_data["sigil_mythic_fallback"]
sigil_priority = sigil_data["sigil_priority"]
sigil_rare_blacklisted = sigil_data["sigil_rare_blacklisted"]
sigil_unknown_rarity = sigil_data["sigil_unknown_rarity"]

global_uniques = uniques["global_uniques"]
simple_mythics = uniques["simple_mythics"]
uniques_with_affixes = uniques["uniques_with_affixes"]
aspect_only_mythic_tests = uniques["aspect_only_mythic_tests"]
