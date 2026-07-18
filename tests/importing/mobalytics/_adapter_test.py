import json
import os
import typing
from types import SimpleNamespace

import pytest

from src.importing import FilenamePart, ImportOptions, ImportRequest
from src.importing.mobalytics import import_mobalytics
from src.item import Dataloader

if typing.TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pytest_mock import MockerFixture
    from selenium.webdriver.remote.webdriver import WebDriver

IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
URLS = [
    "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb",
    "https://mobalytics.gg/diablo-4/builds/barbarian-whirlwind-leveling-barb?ws-ngf5-1=activeVariantId%2C7a9c6d51-18e9-4090-a804-7b73ff00879d",
    "https://mobalytics.gg/diablo-4/builds/necromancer-skeletal-warrior-minions",
    "https://mobalytics.gg/diablo-4/profile/screamheart/builds/15x-thrash-out-of-date",
    "https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
    "https://mobalytics.gg/diablo-4/builds/rogue-efficientrogue-dance-of-knives?ws-ngf5-1=activeVariantId%2Ca2977139-f3e2-4b13-aa64-82ba69972528",
]


def _request(
    *,
    url: str,
    import_aspect_upgrades: bool = True,
    add_to_profiles: bool = False,
    import_greater_affixes: bool = False,
    require_greater_affixes: bool = False,
    custom_file_name: str | None = None,
    filename_parts: tuple[FilenamePart | str, ...] = (FilenamePart.SOURCE, FilenamePart.CLASS),
    export_paragon: bool = False,
) -> ImportRequest:
    return ImportRequest(
        url=url,
        options=ImportOptions(
            import_aspect_upgrades=import_aspect_upgrades,
            add_to_profiles=add_to_profiles,
            import_greater_affixes=import_greater_affixes,
            require_greater_affixes=require_greater_affixes,
            custom_file_name=custom_file_name,
            filename_parts=filename_parts,
            export_paragon=export_paragon,
        ),
    )


class _MobalyticsImportDriver:
    current_url = ""
    title = "Mobalytics"

    def __init__(self, page_source: str) -> None:
        self.page_source = page_source

    def get(self, url: str) -> None:
        self.current_url = url

    def find_element(self, *_args, **_kwargs) -> object:
        return object()

    def quit(self) -> None:
        return None


def _mobalytics_page_source(slots: Sequence[Mapping[str, object]], paragon: Mapping[str, object] | None = None) -> str:
    build_data = {
        "name": "Pulverize Druid",
        "buildVariants": {
            "values": [{"id": "variant-1", "genericBuilder": {"slots": slots}, "paragon": paragon or {}}]
        },
    }
    state = {
        "userGeneratedDocumentBySlug": {
            "data": {
                "data": build_data,
                "tags": {
                    "data": [{"groupSlug": "class", "name": "Druid"}, {"groupSlug": "season", "name": "Season 14"}]
                },
            }
        }
    }
    return f"<html><script>window.__PRELOADED_STATE__={json.dumps(state)};</script></html>"


def _mobalytics_slot(
    slot: str, entity_type: str, title: str, modifiers: Mapping[str, object] | None = None, icon_url: str = ""
) -> dict[str, object]:
    return {
        "gameSlotSlug": slot,
        "gameEntity": {"title": title, "type": entity_type, "iconUrl": icon_url, "modifiers": modifiers, "entity": {}},
    }


def test_import_mobalytics_names_unresolved_weapon_filter_by_slot(mock_ini_loader, mocker: MockerFixture) -> None:
    driver = _MobalyticsImportDriver(
        page_source=_mobalytics_page_source(
            [
                _mobalytics_slot(
                    "weapon",
                    "uniqueItems",
                    "Sundered Night",
                    {"gearStats": [{"id": "strength"}], "implicitStats": None},
                )
            ],
            paragon={
                "boards": [{"board": {"slug": "barbarian-starting-board"}, "glyph": {"slug": ""}, "rotation": 0}],
                "nodes": [{"slug": "barbarian-starting-board-x11-y14"}],
            },
        )
    )
    mocker.patch("src.importing.mobalytics._filters._get_weapon_type_from_slot_tooltip", return_value=None)
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda **kwargs: SimpleNamespace(file_name=kwargs["file_name"])
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)
    result = import_mobalytics(
        request=_request(
            url="https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
            import_aspect_upgrades=False,
            import_greater_affixes=False,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name=None,
            export_paragon=True,
        ),
        driver=typing.cast("WebDriver", driver),
    )
    assert result is not None
    assert result.source_name == "mobalytics"
    assert not result.selected_variant
    profile = profile_store.save_new.call_args.kwargs["profile"]
    assert result.profile is profile
    assert result.paragon is not None
    assert next(iter(profile.affixes[0].root)) == "Weapon"


def test_import_mobalytics_imports_set_charm_and_deduplicates_identical_rings(
    mock_ini_loader, mocker: MockerFixture
) -> None:
    ring_stats = [
        {"id": "willpower"},
        {"id": "critical-strike-chance"},
        {"id": "vulnerable-damage-multiplier"},
        {"id": "critical-strike-damage-multiplier"},
    ]
    slots = [
        _mobalytics_slot("ring-1", "items", "Vulpine's Aspect", {"gearStats": ring_stats, "implicitStats": []}),
        _mobalytics_slot(
            "ring-2", "items", "Archdruid's Aspect", {"gearStats": list(reversed(ring_stats)), "implicitStats": []}
        ),
        _mobalytics_slot(
            "season-12-charm-1",
            "charms",
            "Fer of the Den Mother",
            icon_url="https://cdn.mobalytics.gg/assets/diablo-4/images/charms/might-of-the-den-mother.png",
        ),
    ]
    driver = _MobalyticsImportDriver(page_source=_mobalytics_page_source(slots))
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda **kwargs: SimpleNamespace(file_name=kwargs["file_name"])
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)
    result = import_mobalytics(
        request=_request(
            url="https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
            import_aspect_upgrades=False,
            import_greater_affixes=False,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name=None,
        ),
        driver=typing.cast("WebDriver", driver),
    )
    assert result is not None
    assert result.saved_file_names == ("mobalytics_druid",)
    profile = result.profile
    assert next(iter(profile.affixes[0].root)) == "Ring(x2)"
    assert next(iter(profile.charms[0].root.values())).set == ["might_of_the_den_mother"]


def test_import_mobalytics_imports_seal_identity_with_or_without_affixes(
    mock_ini_loader, mocker: MockerFixture
) -> None:
    slots = [
        _mobalytics_slot("season-12-seal-1", "seals", "Seal of the Diamond Mind"),
        _mobalytics_slot(
            "season-12-seal-2", "seals", "Seal of the Golden Epiphany", {"sealStats": [{"id": "cooldown-reduction"}]}
        ),
    ]
    driver = _MobalyticsImportDriver(page_source=_mobalytics_page_source(slots))
    profile_store = mocker.Mock()
    profile_store.save_new.side_effect = lambda **kwargs: SimpleNamespace(file_name=kwargs["file_name"])
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=profile_store)
    result = import_mobalytics(
        request=_request(
            url="https://mobalytics.gg/diablo-4/builds/druid-zaior-pulverize-druid",
            import_aspect_upgrades=False,
            import_greater_affixes=False,
            require_greater_affixes=False,
            add_to_profiles=False,
            custom_file_name=None,
        ),
        driver=typing.cast("WebDriver", driver),
    )
    assert result is not None
    assert result.paragon is None
    seal_filters = [seal for group in result.profile.seals for seal in group.root.values()]
    assert {seal.unique_aspect[0].name for seal in seal_filters} == {
        "seal_of_the_diamond_mind",
        "seal_of_the_golden_epiphany",
    }
    golden_epiphany = next(seal for seal in seal_filters if seal.unique_aspect[0].name == "seal_of_the_golden_epiphany")
    assert golden_epiphany.affix_pool[0].count[0].name == "cooldown_reduction"


@pytest.mark.parametrize("url", URLS)
@pytest.mark.requests
@pytest.mark.skipif(not IN_GITHUB_ACTIONS, reason="Importer tests are skipped if not run from Github Actions")
def test_import_mobalytics(url: str, mock_ini_loader: MockerFixture, mocker: MockerFixture):
    Dataloader()
    mocker.patch("builtins.open", new=mocker.mock_open())
    import_mobalytics(
        request=_request(
            url=url,
            import_aspect_upgrades=True,
            add_to_profiles=False,
            import_greater_affixes=True,
            require_greater_affixes=True,
            custom_file_name=None,
        )
    )
