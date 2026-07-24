import json
import typing
from types import SimpleNamespace

from src.importing import FilenamePart, ImportOptions, ImportRequest
from src.importing.infinitybuilds import (
    InfinityBuildsParagonCatalog,
    fetch_variants_infinitybuilds,
    import_infinitybuilds,
)
from src.item import Dataloader

if typing.TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pytest_mock import MockerFixture
    from selenium.webdriver.remote.webdriver import WebDriver


class _ImportDriver:
    page_source: str

    def __init__(self, page_source: str) -> None:
        self.page_source = page_source

    def get(self, _url: str) -> None:
        return None

    def find_element(self, *_args, **_kwargs) -> object:
        return object()


def _request(
    *,
    url: str,
    import_charms: bool = True,
    import_seals: bool = True,
    custom_file_name: str | None = None,
    export_paragon: bool = False,
    filename_parts: tuple[FilenamePart | str, ...] = (FilenamePart.SOURCE, FilenamePart.VARIANT),
    multi_build: bool = False,
) -> ImportRequest:
    return ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=True,
            import_charms=import_charms,
            import_seals=import_seals,
            import_greater_affixes=True,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name=custom_file_name,
            filename_parts=filename_parts,
            export_paragon=export_paragon,
            multi_build=multi_build,
        ),
    )


def test_import_infinitybuilds_passes_category_options_to_pipeline_config(mocker) -> None:
    run_import = mocker.patch("src.importing.infinitybuilds.adapter._import_infinitybuilds", return_value=None)
    request = _request(
        url="https://infinitybuilds.gg/en/builds/barbarian-example", import_charms=False, import_seals=False
    )

    import_infinitybuilds(request, driver=typing.cast("WebDriver", object()))

    captured_request = run_import.call_args.args[0]
    assert not captured_request.options.import_charms
    assert not captured_request.options.import_seals


def _gear_piece(slot: str, item_id: str, affix_ids: list[str]) -> dict[str, object]:
    return {
        "kind": "custom_legendary",
        "slot": slot,
        "itemId": item_id,
        "affixes": [{"affixId": value} for value in affix_ids],
    }


def _page_source(class_id: str, variants: Sequence[Mapping[str, object]]) -> str:
    payload = json.dumps({"classId": class_id, "variants": variants}, separators=(",", ":"))
    chunk = f"self.__next_f.push([1,{json.dumps(payload)}])"
    return f"<html><script>{chunk}</script></html>"


def test_fetch_variants_assigns_fallback_ids_after_skipping_empty_variants() -> None:
    driver = _ImportDriver(
        _page_source(
            "barbarian",
            [{"name": "Empty", "gear": []}, {"name": "Unnamed", "gear": [_gear_piece("chest", "item-chest-1", [])]}],
        )
    )

    variants = fetch_variants_infinitybuilds(
        request=ImportRequest("https://infinitybuilds.gg/en/builds/barbarian-example"),
        driver=typing.cast("WebDriver", driver),
    )

    assert [(variant.id, variant.name) for variant in variants] == [("0", "Unnamed")]


def test_import_infinitybuilds_saves_one_profile_per_variant_and_resolves_gear_once(
    mock_ini_loader, mocker: MockerFixture
) -> None:
    Dataloader()
    variants = [
        {
            "id": "v-1",
            "name": "Variant One",
            "gear": [_gear_piece("chest", "item-chest-1", ["affix-armor"])],
            "paragon": {"slots": [], "glyphs": {}, "activeNodes": ["paragon-board::paragon-unknown-99::0"]},
        },
        {"id": "v-2", "name": "Variant Two", "gear": [_gear_piece("chest", "item-chest-2", ["affix-armor"])]},
    ]
    driver = _ImportDriver(_page_source("barbarian", variants))
    response = mocker.Mock()
    response.json.return_value = {
        "dataset": {
            "gear": {
                "items": [
                    {"id": "item-chest-1", "label": "Item One", "rarity": "legendary", "slot": "Chest Armor"},
                    {"id": "item-chest-2", "label": "Item Two", "rarity": "legendary", "slot": "Chest Armor"},
                ],
                "aspects": [],
                "affixes": [{"id": "affix-armor", "label": "Armor", "greaterAffixEligible": False}],
            }
        }
    }
    get_with_retry = mocker.patch("src.importing.infinitybuilds.extraction.get_with_retry", return_value=response)
    mocker.patch(
        "src.importing.infinitybuilds.adapter.fetch_infinitybuilds_paragon_catalog",
        return_value=InfinityBuildsParagonCatalog(board_labels={}, glyph_labels={}),
    )
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda **kwargs: SimpleNamespace(file_name=kwargs["file_name"])
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)
    result = import_infinitybuilds(
        request=_request(url="https://infinitybuilds.gg/en/builds/barbarian-example", export_paragon=True),
        driver=typing.cast("WebDriver", driver),
    )
    assert result is not None
    assert result.source_name == "infinitybuilds"
    assert result.selected_variant == "Variant One"
    assert result.saved_file_names == ("infinitybuilds_variant_one", "infinitybuilds_variant_two")
    assert result.paragon is not None
    assert get_with_retry.call_count == 1
    assert "itemIds=item-chest-1%2Citem-chest-2" in get_with_retry.call_args[0][0]
    assert profile_store.save_new.call_count == 2


def test_import_infinitybuilds_imports_talisman_charms_and_seal(mock_ini_loader, mocker: MockerFixture) -> None:
    Dataloader()
    variants = [
        {
            "id": "v-1",
            "name": "Main",
            "gear": [_gear_piece("chest", "item-chest", ["affix-armor"])],
            "talisman": {
                "seal": "item-1128-talisman-seal-qst-skovos-atanos-mephisto-itm",
                "charms": ["Talisman_Charm_Set_Barb_01_03", "Talisman_Charm_Unique_S05_BSK_Gloves_Unique_Generic_001"],
                "charmAffixes": [["affix-charm-all-stats", None], [None, None]],
                "charmAffixValues": [[100, None], [None, None]],
                "charmAffixGreater": [[False, None], [None, None]],
            },
        }
    ]
    driver = _ImportDriver(_page_source("barbarian", variants))
    response = mocker.Mock()
    response.json.return_value = {
        "dataset": {
            "gear": {
                "items": [
                    {"id": "item-chest", "label": "Chest", "rarity": "legendary", "slot": "Chest Armor"},
                    {
                        "id": "item-talisman-charm-set-barb-01-03-itm",
                        "sourceId": "Talisman_Charm_Set_Barb_01_03.itm",
                        "label": "Mlor of Sescheron's Fury",
                        "rarity": "normal",
                        "slot": "Charm",
                    },
                    {
                        "id": "item-talisman-charm-unique-s05-bsk-gloves-unique-generic-001-itm",
                        "sourceId": "Talisman_Charm_Unique_S05_BSK_Gloves_Unique_Generic_001.itm",
                        "label": "Endurant Faith",
                        "rarity": "unique",
                        "slot": "Charm",
                    },
                    {
                        "id": "item-talisman-seal-qst-skovos-atanos-mephisto-itm",
                        "sourceId": "Talisman_Seal_QST_Skovos_Atanos_Mephisto.itm",
                        "label": "Legendary Horadric Seal",
                        "rarity": "legendary",
                        "slot": "Horadric Seal",
                    },
                ],
                "aspects": [],
                "affixes": [
                    {"id": "affix-armor", "label": "Armor", "greaterAffixEligible": False},
                    {"id": "affix-charm-all-stats", "label": "All Stats", "greaterAffixEligible": False},
                ],
            }
        }
    }
    get_with_retry = mocker.patch("src.importing.infinitybuilds.extraction.get_with_retry", return_value=response)
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda **kwargs: SimpleNamespace(file_name=kwargs["file_name"])
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)

    result = import_infinitybuilds(
        request=_request(url="https://infinitybuilds.gg/en/builds/barbarian-example"),
        driver=typing.cast("WebDriver", driver),
    )

    assert result is not None
    profile = result.profile
    charms = [charm for group in profile.charms for charm in group.root.values()]
    assert {charm.set[0] for charm in charms if charm.set} == {"sescherons_fury"}
    assert {charm.unique_aspect[0].name for charm in charms if charm.unique_aspect} == {"endurant_faith"}
    set_charm = next(charm for charm in charms if charm.set)
    assert set_charm.affix_pool[0].count[0].name == "all_stats"
    assert [rarity.value for rarity in set_charm.rarities] == ["common"]
    seals = [seal for group in profile.seals for seal in group.root.values()]
    assert len(seals) == 1
    assert [rarity.value for rarity in seals[0].rarities] == ["legendary"]
    called_url = get_with_retry.call_args.args[0]
    assert "Talisman_Charm_Set_Barb_01_03" in called_url
    assert "item-talisman-seal-qst-skovos-atanos-mephisto-itm" in called_url
