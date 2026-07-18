import json
import typing
from types import SimpleNamespace

from src.importing import FilenamePart, ImportOptions, ImportRequest
from src.importing.infinitybuilds import import_infinitybuilds
from src.importing.paragon import InfinityBuildsParagonCatalog
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
    custom_file_name: str | None = None,
    export_paragon: bool = False,
    filename_parts: tuple[FilenamePart | str, ...] = (FilenamePart.SOURCE, FilenamePart.VARIANT),
) -> ImportRequest:
    return ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=True,
            import_greater_affixes=True,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name=custom_file_name,
            filename_parts=filename_parts,
            export_paragon=export_paragon,
        ),
    )


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
    get_with_retry = mocker.patch("src.importing.infinitybuilds._extraction.get_with_retry", return_value=response)
    mocker.patch(
        "src.importing.infinitybuilds._adapter.fetch_infinitybuilds_paragon_catalog",
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
