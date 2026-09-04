import enum
import importlib
import json
import typing
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast

import src.item.filter.engine as engine_module
from src.item import Affix, Aspect, Item
from src.item.filter import Filter
from src.item.filter.rules import LoadedRules
from src.profiles import ProfileModel

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from src.type_aliases import JsonValue


type FixtureValue = (
    JsonValue | Affix | Aspect | Item | ProfileModel | enum.Enum | list[FixtureValue] | dict[str, FixtureValue]
)
type ItemListCase = tuple[str, list[str], Item]
type ItemBooleanCase = tuple[str, bool, Item]


class _FilterFixtures(Protocol):
    affix: ProfileModel
    affix_rarity: ProfileModel
    always_keep_mythics: ProfileModel
    aspects_filters: ProfileModel
    global_unique: ProfileModel
    seal_charm: ProfileModel
    sigil: ProfileModel
    sigil_blacklist_only: ProfileModel
    sigil_priority: ProfileModel
    sigil_rarity_rare_only: ProfileModel
    sigil_rarity_rare_with_blacklist: ProfileModel
    sigil_rarity_rare_with_whitelist: ProfileModel
    sigil_whitelist_only: ProfileModel
    tributes: ProfileModel
    unique_affixes: ProfileModel


class _FixtureConstructor(Protocol):
    def __call__(self, *args: FixtureValue, **kwargs: FixtureValue) -> FixtureValue: ...


def _type(name: str) -> _FixtureConstructor:
    module, _, qualname = name.rpartition(".")
    value = importlib.import_module(module)
    for part in qualname.split("."):
        value = getattr(value, part)
    return cast("_FixtureConstructor", value)


def _mapping(value: FixtureValue) -> dict[str, FixtureValue]:
    return cast("dict[str, FixtureValue]", value)


def _create_mocked_filter(mocker: MockerFixture) -> Filter:
    filter_obj = Filter()
    filter_obj.rules = LoadedRules.empty()
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
    return settings


def _decode(value: FixtureValue) -> FixtureValue:
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    value = _mapping(value)
    if "__enum__" in value:
        return cast("FixtureValue", getattr(_type(cast("str", value["__enum__"])), cast("str", value["value"])))
    if "__class__" in value:
        cls = _type(cast("str", value["__class__"]))
        fields = _mapping(_decode(value["fields"]))
        try:
            return cls(**fields)
        except TypeError:
            return cls(fields)
    return {key: _decode(item) for key, item in value.items()}


with (Path(__file__).parent / "data" / "fixtures.json").open(encoding="utf-8") as fixture_file:
    _fixtures = _mapping(_decode(cast("FixtureValue", json.load(fixture_file))))

affixes = cast("list[ItemListCase]", _mapping(_fixtures["affixes"])["affixes"])
aspects = cast("list[ItemListCase]", _mapping(_fixtures["aspects"])["aspects"])
charms = cast("list[ItemListCase]", _mapping(_fixtures["charms"])["charms"])
filters = cast("_FilterFixtures", type("Filters", (), _mapping(_fixtures["filters"]))())
items = cast("list[ItemListCase]", _mapping(_fixtures["items"])["items"])
seals = cast("list[ItemListCase]", _mapping(_fixtures["seals"])["seals"])
sigil_data = _mapping(_fixtures["sigils"])
tributes = cast("list[ItemListCase]", _mapping(_fixtures["tributes"])["tributes"])
uniques = _mapping(_fixtures["uniques"])

sigils = cast("list[ItemListCase]", sigil_data["sigils"])
sigil_derived_legendary = cast("Item", sigil_data["sigil_derived_legendary"])
sigil_derived_rare = cast("Item", sigil_data["sigil_derived_rare"])
sigil_jalal = cast("Item", sigil_data["sigil_jalal"])
sigil_mythic_fallback = cast("Item", sigil_data["sigil_mythic_fallback"])
sigil_priority = cast("Item", sigil_data["sigil_priority"])
sigil_rare_blacklisted = cast("Item", sigil_data["sigil_rare_blacklisted"])
sigil_unknown_rarity = cast("Item", sigil_data["sigil_unknown_rarity"])

global_uniques = cast("list[ItemListCase]", uniques["global_uniques"])
simple_mythics = cast("list[ItemBooleanCase]", uniques["simple_mythics"])
uniques_with_affixes = cast("list[ItemListCase]", uniques["uniques_with_affixes"])
aspect_only_mythic_tests = cast("list[ItemBooleanCase]", uniques["aspect_only_mythic_tests"])
