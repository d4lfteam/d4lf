import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast, override

import pytest

from src.game_data import GameCatalog
from src.importing import ImportOptions, ImportRequest, VariantSelection
from src.importing.d2core import D2CoreImportSource
from src.importing.d2core.browser import BrowserSnapshot
from src.importing.d2core.catalog import CatalogTransport
from src.importing.d2core.errors import PRIVATE_ACCESS, D2CoreImportError
from src.importing.d2core.source import PlannerSnapshot

FIXTURE_ROOT = Path(__file__).parent.parent / "data"


class CatalogFixture(CatalogTransport):
    def __init__(self, affix_key: str, affix_name: str) -> None:
        self.responses = {"affix": {"affix": [{"key": affix_key, "name": affix_name, "desc": affix_name}]}}
        self.urls: list[str] = []

    @override
    def get(self, url: str, *, timeout: float) -> object:
        del timeout
        self.urls.append(url)
        return self.responses[url.rsplit("/", maxsplit=1)[-1].split("_", maxsplit=1)[0]]


class FixtureCatalog(CatalogTransport):
    def __init__(self) -> None:
        self.responses = json.loads((FIXTURE_ROOT / "catalogs.json").read_text())
        self.urls: list[str] = []

    @override
    def get(self, url: str, *, timeout: float) -> object:
        del timeout
        self.urls.append(url)
        kind = url.rsplit("/", maxsplit=1)[-1].split("_", maxsplit=1)[0]
        return self.responses[kind]


def _fixture(name: str) -> dict[str, object]:
    return cast("dict[str, object]", json.loads((FIXTURE_ROOT / name).read_text()))


def _import_fixture(mocker, name: str, request: ImportRequest):
    build = _fixture(name)
    catalog = FixtureCatalog()
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)
    source = D2CoreImportSource(
        snapshot=PlannerSnapshot(
            build=build, catalog_url="https://cloudstorage.d2core.com/data/d4/fixture/affix_enUS.json"
        ),
        catalog_transport=catalog,
    )
    return source.import_build(request), catalog, source, store


def _snapshot() -> tuple[BrowserSnapshot, CatalogFixture]:
    catalog = GameCatalog()
    affix_key, affix_name = next(iter(catalog.affix_dict.items()))
    build = {
        "_id": "offline",
        "is_public": True,
        "deleted": False,
        "char": "Druid",
        "title": "Offline Build",
        "season": "opaque-season",
        "variants": [
            {"name": "Duplicate", "gear": {"0": {"type": "rare", "itemType": "Helm", "mods": [{"name": affix_key}]}}},
            {"name": "Duplicate", "gear": {}},
            {"name": "", "gear": {"0": {"type": "rare", "itemType": "Helm", "mods": [{"name": affix_key}]}}},
        ],
    }
    body = {"data": {"response_data": json.dumps({"data": build})}}
    catalog = CatalogFixture(affix_key, affix_name)
    return BrowserSnapshot(body, "https://cloudstorage.d2core.com/data/d4/v1/affix_enUS.json"), catalog


def _snapshot_build(snapshot: BrowserSnapshot) -> dict[str, object]:
    body = cast("dict[str, object]", snapshot.response_body)
    data = cast("dict[str, object]", body["data"])
    return cast("dict[str, object]", json.loads(str(data["response_data"])))


def _replace_snapshot_build(snapshot: BrowserSnapshot, build: dict[str, object]) -> None:
    body = cast("dict[str, object]", snapshot.response_body)
    data = cast("dict[str, object]", body["data"])
    data["response_data"] = json.dumps(build)


def test_source_discovers_all_variants_and_imports_selected_snapshot_once(mocker) -> None:
    snapshot, catalog = _snapshot()
    source = D2CoreImportSource(snapshot=snapshot, catalog_transport=catalog)
    request = ImportRequest("https://www.d2core.com/d4/planner?bd=offline&lang=zhCN")
    assert [(item.id, item.name) for item in source.fetch_variants(request)] == [
        ("1", "Duplicate"),
        ("2", "Duplicate"),
        ("3", "Variant 3"),
    ]
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)
    result = source.import_build(
        ImportRequest(
            url=request.url,
            options=ImportOptions(multi_build=True, custom_file_name="offline"),
            variant_selection=VariantSelection(("3", "1", "3")),
        )
    )

    assert result.source_name == "d2core"
    assert result.saved_file_names == ("offline_1", "offline_2")
    assert store.save_new.call_count == 2
    assert source.closed
    assert source.snapshot is None
    assert len(catalog.urls) == 1


def test_source_single_variant_uses_url_position_and_falls_back_to_first(mocker) -> None:
    snapshot, catalog = _snapshot()
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)

    selected = D2CoreImportSource(snapshot=snapshot, catalog_transport=catalog).import_build(
        ImportRequest(
            "https://d2core.com/d4/planner?bd=offline&var=3", options=ImportOptions(custom_file_name="chosen")
        )
    )
    assert selected.selected_variant == "Variant 3"
    assert selected.saved_file_name == "chosen"


def test_source_decodes_string_response_body(mocker) -> None:
    snapshot, catalog = _snapshot()
    string_snapshot = BrowserSnapshot(json.dumps(snapshot.response_body), snapshot.catalog_url)
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)

    result = D2CoreImportSource(snapshot=string_snapshot, catalog_transport=catalog).import_build(
        ImportRequest("https://d2core.com/d4/planner?bd=offline", options=ImportOptions(custom_file_name="chosen"))
    )
    assert result.source_name == "d2core"


def test_source_validates_direct_snapshots_and_cleans_them_after_failure() -> None:
    source = D2CoreImportSource(
        snapshot=PlannerSnapshot(
            build={"_id": "offline", "is_public": False, "deleted": False, "variants": []},
            catalog_url="https://cloudstorage.d2core.com/data/d4/v1/affix_enUS.json",
        )
    )

    with pytest.raises(D2CoreImportError) as error:
        source.fetch_variants(ImportRequest("https://d2core.com/d4/planner?bd=offline"))
    assert error.value.code == PRIVATE_ACCESS
    assert source.closed
    assert source.snapshot is None


def test_source_fetches_optional_catalogs_only_for_enabled_supported_data(mocker, caplog) -> None:
    snapshot, catalog = _snapshot()
    build = _snapshot_build(snapshot)
    data = cast("dict[str, object]", build["data"])
    variants = cast("list[dict[str, object]]", data["variants"])
    variants[0]["name"] = "Equipment"
    variants[1]["name"] = "Optional"
    variants[1]["gear"] = variants[0]["gear"]
    variants[1]["charms"] = [{"type": "charm", "key": "missing"}]
    _replace_snapshot_build(snapshot, build)
    catalog.responses["talisman"] = {"unexpected": []}
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)
    caplog.set_level("INFO")

    source = D2CoreImportSource(snapshot=snapshot, catalog_transport=catalog)
    source.import_build(
        ImportRequest(
            "https://d2core.com/d4/planner?bd=offline",
            options=ImportOptions(multi_build=True, custom_file_name="offline"),
            variant_selection=VariantSelection(("1", "2")),
        )
    )
    assert [url.split("?", maxsplit=1)[0].rsplit("/", maxsplit=1)[-1] for url in catalog.urls] == [
        "affix_enUS.json",
        "talisman_enUS.json",
    ]
    warnings = [record.getMessage() for record in caplog.records if "D2C-W121" in record.getMessage()]
    assert len(warnings) == 1
    assert "Optional" in warnings[0]
    assert "Equipment" not in warnings[0]
    assert any("created_profiles=2 warnings=1" in record.getMessage() for record in caplog.records)


def test_source_ignores_inherently_unsupported_talisman_entries(mocker, caplog) -> None:
    snapshot, catalog = _snapshot()
    build = _snapshot_build(snapshot)
    data = cast("dict[str, object]", build["data"])
    variants = cast("list[dict[str, object]]", data["variants"])
    variants[0]["charms"] = [{"type": "skill", "key": "not-a-talisman"}]
    gear = cast("dict[str, dict[str, object]]", variants[0]["gear"])
    gear["0"].update(type="legendary", key="unsupported", transfiguredAspect="crafted")
    _replace_snapshot_build(snapshot, build)
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)
    caplog.set_level("WARNING")

    source = D2CoreImportSource(snapshot=snapshot, catalog_transport=catalog)
    source.import_build(ImportRequest("https://d2core.com/d4/planner?bd=offline", options=ImportOptions()))

    assert [url.split("?", maxsplit=1)[0].rsplit("/", maxsplit=1)[-1] for url in catalog.urls] == ["affix_enUS.json"]
    assert not any("D2C-W12" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize(
    ("fixture_name", "variant_count"), [("planner_2216.json", 5), ("planner_1ZsP.json", 9), ("planner_2268.json", 1)]
)
def test_sanitized_planner_fixtures_discover_offline(fixture_name: str, variant_count: int) -> None:
    build = _fixture(fixture_name)
    source = D2CoreImportSource(
        snapshot=PlannerSnapshot(
            build=build, catalog_url="https://cloudstorage.d2core.com/data/d4/fixture/affix_enUS.json"
        )
    )
    variants = source.fetch_variants(ImportRequest(f"https://d2core.com/d4/planner?bd={build['_id']}"))

    assert len(variants) == variant_count
    assert [variant.id for variant in variants] == [str(index) for index in range(1, variant_count + 1)]
    assert all(variant.name for variant in variants)


def test_compact_sanitized_fixture_completes_offline_import(mocker) -> None:
    result, catalog, source, _ = _import_fixture(
        mocker,
        "planner_2268.json",
        ImportRequest("https://d2core.com/d4/planner?bd=2268", options=ImportOptions(custom_file_name="fixture")),
    )

    assert result.saved_file_name == "fixture"
    assert result.profile.affixes
    assert [url.split("?", maxsplit=1)[0].rsplit("/", maxsplit=1)[-1] for url in catalog.urls] == ["affix_enUS.json"]
    assert source.closed
    assert source.snapshot is None


def test_discovery_boundary_fixture_imports_usable_variants_and_skips_narrative(mocker, caplog) -> None:
    caplog.set_level("WARNING")
    result, _, source, _ = _import_fixture(
        mocker,
        "planner_2216.json",
        ImportRequest(
            "https://d2core.com/d4/planner?bd=2216",
            options=ImportOptions(multi_build=True, custom_file_name="boundary", export_paragon=True),
            variant_selection=VariantSelection(tuple(str(index) for index in range(1, 6))),
        ),
    )

    assert len(result.saved_file_names) == 3
    assert sum("D2C-W102" in record.getMessage() for record in caplog.records) == 2
    assert source.closed


def test_supported_module_fixture_imports_its_matrix_offline(mocker) -> None:
    result, _, source, store = _import_fixture(
        mocker,
        "planner_1ZsP.json",
        ImportRequest(
            "https://d2core.com/d4/planner?bd=1ZsP",
            options=ImportOptions(
                multi_build=True, custom_file_name="matrix", import_greater_affixes=True, export_paragon=True
            ),
            variant_selection=VariantSelection(tuple(str(index) for index in range(1, 10))),
        ),
    )

    assert len(result.saved_file_names) == 9
    profiles = {call.kwargs["file_name"]: call.kwargs["profile"] for call in store.save_new.call_args_list}
    assert profiles["matrix_2"].aspect_upgrades == ["accelerating"]
    assert profiles["matrix_3"].affixes[0].root["Helm"].unique_aspect[0].name == "100000_steps"
    assert profiles["matrix_4"].charms[0].root["Charm"].affix_pool[0].count[0].name == "all_stats"
    assert profiles["matrix_4"].charms[0].root["Charm"].set == ["survival"]
    assert profiles["matrix_5"].seals[0].root["HoradricSeal"].affix_pool[0].count[0].name == (
        "adept_action_damage_reduction_while_moving"
    )
    assert profiles["matrix_6"].affixes[0].root["Helm"].affix_pool[0].count[0].want_greater
    assert profiles["matrix_7"].paragon.paragon_boards_list[0][0].board_id == "fixture-board"
    assert source.closed
