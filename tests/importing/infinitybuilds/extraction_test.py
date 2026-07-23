import json
import typing
from types import SimpleNamespace

import lxml.html
import pytest

from src.importing import ImportOptions, ImportRequest
from src.importing.infinitybuilds import import_infinitybuilds
from src.importing.infinitybuilds.extraction import (
    _convert_raw_to_affixes,
    _extract_balanced,
    _extract_build_data,
    _extract_build_title,
    _normalize_aspect_name,
    _resolve_gear_data,
)
from src.item import Dataloader

if typing.TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pytest_mock import MockerFixture
    from selenium.webdriver.remote.webdriver import WebDriver


def _request(
    *,
    url: str,
    import_aspect_upgrades: bool = True,
    add_to_profiles: bool = False,
    import_greater_affixes: bool = False,
    require_greater_affixes: bool = False,
    custom_file_name: str | None = None,
) -> ImportRequest:
    return ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=import_aspect_upgrades,
            add_to_profiles=add_to_profiles,
            import_greater_affixes=import_greater_affixes,
            require_greater_affixes=require_greater_affixes,
            custom_file_name=custom_file_name,
        ),
    )


class _InfinityBuildsImportDriver:
    current_url = ""
    title = "InfinityBuilds"

    def __init__(self, page_source: str) -> None:
        self.page_source = page_source

    def get(self, url: str) -> None:
        self.current_url = url

    def find_element(self, *_args, **_kwargs) -> object:
        return object()

    def quit(self) -> None:
        return None


def _push_chunk(payload: Mapping[str, object]) -> str:
    # Mirrors InfinityBuilds' React Flight payload: a JSON-encoded string embedded in a
    # self.__next_f.push([id, "<json-string>"]) call, with the interesting data (classId, variants)
    # inside that string. Real payloads are minified (no spaces around separators), which matters
    # since _extract_build_data's classId regex expects `"classId":"..."` with no space.
    inner = json.dumps(payload, separators=(",", ":"))
    return f"self.__next_f.push([1,{json.dumps(inner)}])"


def _infinitybuilds_page_source(
    class_id: str, variants: Sequence[Mapping[str, object]], title: str = "Test Build"
) -> str:
    payload = {"classId": class_id, "variants": variants}
    script = _push_chunk(payload)
    return f"<html><head><title>{title} | InfinityBuilds</title></head><body><script>{script}</script></body></html>"


def _gear_piece(
    slot: str, item_id: str, affix_ids: list[str], kind: str = "custom_legendary", aspect_id: str | None = None
) -> dict[str, object]:
    piece = {
        "kind": kind,
        "slot": slot,
        "itemId": item_id,
        "affixes": [{"value": 100, "affixId": affix_id, "swapped": True, "tempered": False} for affix_id in affix_ids],
    }
    if aspect_id:
        piece["aspectId"] = aspect_id
    return piece


def test_extract_balanced_handles_nested_strings_with_escaped_quotes() -> None:
    text = '{"a": [1, {"b": "he said \\"hi\\""}, 2]}'
    start = text.index("[")

    extracted = _extract_balanced(text, start, "[", "]")

    assert json.loads(extracted) == [1, {"b": 'he said "hi"'}, 2]


def test_extract_build_title_reads_page_before_pipe_separator() -> None:
    data = lxml.html.fromstring("<html><head><title>Whirlwind Barb | InfinityBuilds</title></head></html>")

    assert _extract_build_title(data) == "Whirlwind Barb"


def test_extract_build_data_parses_flight_chunk_and_bracket_matches_variants() -> None:
    variants = [{"id": "v-1", "name": "Variant One", "gear": [_gear_piece("helm", "item-1", ["affix-1"])]}]
    data = lxml.html.fromstring(_infinitybuilds_page_source("barbarian", variants))

    build_data = _extract_build_data(data)

    assert build_data == {"classId": "barbarian", "variants": variants}


def test_extract_build_data_returns_none_when_no_matching_script() -> None:
    data = lxml.html.fromstring("<html><script>console.log('nothing here')</script></html>")

    assert _extract_build_data(data) is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Edgemaster's Aspect", "edgemasters"),
        ("Aspect of Channeling", "of_channeling"),
        ("Crushing Aspect", "crushing"),
    ],
)
def test_normalize_aspect_name_strips_the_word_aspect(name: str, expected: str) -> None:
    assert _normalize_aspect_name(name) == expected


def test_convert_raw_to_affixes_skips_tempered_affixes() -> None:
    # Tempered affixes (e.g. a tempered "Physical Damage" roll) are applied via the Tempering
    # system, not innate item rolls, so they must not be treated as filterable gear affixes.
    Dataloader()  # ensure real affix data is loaded before we assert against it
    raw_affixes = [
        {"affixId": "affix-strength", "value": 100},
        {"affixId": "affix-physical-damage-tempered", "value": 50, "tempered": True},
    ]
    resolved_affixes = {
        "affix-strength": {"label": "Strength", "greaterAffixEligible": False},
        "affix-physical-damage-tempered": {"label": "Physical Damage", "greaterAffixEligible": False},
    }

    affixes = _convert_raw_to_affixes(raw_affixes, resolved_affixes)

    assert [a.name for a in affixes] == ["strength"]


def test_resolve_gear_data_queries_view_endpoint_with_unique_sorted_ids(mocker: MockerFixture) -> None:
    gear = [
        _gear_piece("helm", "item-1", ["affix-1", "affix-2"], aspect_id="aspect-1"),
        _gear_piece("chest", "item-2", ["affix-1"]),
    ]
    response = mocker.Mock()
    response.json.return_value = {
        "dataset": {
            "gear": {
                "items": [{"id": "item-1", "label": "Item One"}, {"id": "item-2", "label": "Item Two"}],
                "aspects": [{"id": "aspect-1", "label": "Aspect One"}],
                "affixes": [{"id": "affix-1", "label": "Affix One"}, {"id": "affix-2", "label": "Affix Two"}],
            }
        }
    }
    get_with_retry = mocker.patch("src.importing.infinitybuilds.extraction.get_with_retry", return_value=response)

    resolved = _resolve_gear_data("barbarian", gear)

    called_url = get_with_retry.call_args[0][0]
    assert "classId=barbarian" in called_url
    assert "mode=view" in called_url
    assert "itemIds=item-1%2Citem-2" in called_url
    assert "aspectIds=aspect-1" in called_url
    assert "affixIds=affix-1%2Caffix-2" in called_url
    assert resolved.items["item-1"]["label"] == "Item One"
    assert resolved.aspects["aspect-1"]["label"] == "Aspect One"
    assert resolved.affixes["affix-2"]["label"] == "Affix Two"


def test_import_infinitybuilds_maps_gear_and_aspect_upgrades(mock_ini_loader, mocker: MockerFixture) -> None:
    Dataloader()  # ensure real affix/aspect data is loaded before we assert against it
    variants = [
        {
            "id": "v-1",
            "name": "Main Variant",
            "gear": [
                _gear_piece(
                    "chest",
                    "item-chest",
                    ["affix-strength", "affix-life", "affix-armor"],
                    kind="custom_legendary",
                    aspect_id="aspect-channeling",
                ),
                _gear_piece("helm", "item-helm-unique", ["affix-armor"], kind="unique"),
                _gear_piece("gloves", "item-mythic", [], kind="mythic"),
            ],
        }
    ]
    driver = _InfinityBuildsImportDriver(page_source=_infinitybuilds_page_source("barbarian", variants))

    response = mocker.Mock()
    response.json.return_value = {
        "dataset": {
            "gear": {
                "items": [
                    {"id": "item-chest", "label": "Warlord Leg Plates", "rarity": "legendary", "slot": "Chest Armor"},
                    {
                        "id": "item-helm-unique",
                        "label": "Tuskhelm of Joritz the Mighty",
                        "rarity": "unique",
                        "slot": "Helm",
                    },
                    {"id": "item-mythic", "label": "Doombringer", "rarity": "mythic", "slot": "Gloves"},
                ],
                "aspects": [{"id": "aspect-channeling", "label": "Aspect of Channeling"}],
                "affixes": [
                    {
                        "id": "affix-strength",
                        "label": "Strength",
                        "greaterAffixEligible": True,
                        "valueRange": {"max": 100},
                    },
                    {"id": "affix-life", "label": "Maximum Life", "greaterAffixEligible": False},
                    {"id": "affix-armor", "label": "Armor", "greaterAffixEligible": False},
                ],
            }
        }
    }
    mocker.patch("src.importing.infinitybuilds.extraction.get_with_retry", return_value=response)

    captured_profile = {}

    def fake_save_new(*, file_name, profile, source):
        captured_profile["profile"] = profile
        return SimpleNamespace(file_name=file_name)

    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = fake_save_new
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    import_infinitybuilds(
        request=_request(
            url="https://infinitybuilds.gg/en/builds/barbarian-fL8P6vVSqI",
            import_aspect_upgrades=True,
            import_greater_affixes=True,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name="test",
        ),
        driver=typing.cast("WebDriver", driver),
    )

    profile = captured_profile["profile"]
    assert profile.aspect_upgrades == ["of_channeling"]
    filter_names = {next(iter(entry.root)) for entry in profile.affixes}
    assert filter_names == {"ChestArmor", "Helm", "Gloves"}
    helm_filter = next(entry.root["Helm"] for entry in profile.affixes if "Helm" in entry.root)
    assert helm_filter.unique_aspect[0].name == "tuskhelm_of_joritz_the_mighty"
    chest_filter = next(entry.root["ChestArmor"] for entry in profile.affixes if "ChestArmor" in entry.root)
    affix_names = {affix.name for affix in chest_filter.affix_pool[0].count}
    assert affix_names == {"strength", "maximum_life", "armor"}
    strength_affix = next(a for a in chest_filter.affix_pool[0].count if a.name == "strength")
    assert strength_affix.want_greater is True
    gloves_filter = next(entry.root["Gloves"] for entry in profile.affixes if "Gloves" in entry.root)
    assert gloves_filter.unique_aspect[0].name == "doombringer"
    assert gloves_filter.affix_pool == []
