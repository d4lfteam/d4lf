import json
import threading

import pytest

from src.game_data import GameCatalog, ItemType
from src.game_data import catalog as catalog_module
from src.game_data.catalog import _load_string_map
from src.item import Item, ItemJSONEncoder


class _LoaderFailure(BaseException):
    pass


def test_load_string_map_returns_string_values(tmp_path) -> None:
    path = tmp_path / "strings.json"
    path.write_text(json.dumps({"first": "one", "second": "two"}), encoding="utf-8")

    assert _load_string_map(path) == {"first": "one", "second": "two"}


@pytest.mark.parametrize("payload", [[], {"first": 1}, {"first": None}])
def test_load_string_map_rejects_non_string_maps(tmp_path, payload) -> None:
    path = tmp_path / "strings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="only string keys and values"):
        _load_string_map(path)


def test_catalog_has_expected_data_containers() -> None:
    assert isinstance(GameCatalog.affix_dict, dict)
    assert isinstance(GameCatalog.aspect_list, list)


def test_catalog_reload_keeps_item_type_values_canonical() -> None:
    catalog = GameCatalog()
    canonical_values = {item_type: item_type.value for item_type in ItemType}

    catalog.load_data()

    assert {item_type: item_type.value for item_type in ItemType} == canonical_values


def test_catalog_resolves_item_type_names_values_and_labels(monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "item_types_dict", {**catalog.item_types_dict, "Helm": "Casque", "Incense": "Encens"})

    assert catalog.item_type_label(ItemType.Helm) == "Casque"
    assert catalog.item_type_from_text("Helm") is ItemType.Helm
    assert catalog.item_type_from_text("helm") is ItemType.Helm
    assert catalog.item_type_from_text("  casque ") is ItemType.Helm
    assert catalog.item_type_from_text("encens") is ItemType.Incense
    assert catalog.item_type_from_text("unknown") is None


def test_item_type_serialization_uses_canonical_value_after_catalog_load() -> None:
    catalog = GameCatalog()
    catalog.load_data()

    encoded = json.dumps(Item(item_type=ItemType.Incense), cls=ItemJSONEncoder)

    assert '"item_type": "incense"' in encoded


def test_catalog_retries_after_failed_initialization(monkeypatch) -> None:
    monkeypatch.setattr(GameCatalog, "_instance", None)
    monkeypatch.setattr(GameCatalog, "data_loaded", False)
    attempts = 0

    def load_data(instance) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            message = "load failed"
            raise RuntimeError(message)
        instance.affix_dict = {"ready": "yes"}

    monkeypatch.setattr(GameCatalog, "load_data", load_data)
    with pytest.raises(RuntimeError, match="load failed"):
        GameCatalog()
    assert GameCatalog._instance is None
    assert GameCatalog.data_loaded is False

    instance = GameCatalog()
    assert instance.data_loaded is True
    assert instance.affix_dict == {"ready": "yes"}


def test_catalog_initialization_is_serialized(monkeypatch) -> None:
    monkeypatch.setattr(GameCatalog, "_instance", None)
    monkeypatch.setattr(GameCatalog, "data_loaded", False)
    started = threading.Event()
    release = threading.Event()
    instances = []

    def load_data(instance) -> None:
        started.set()
        assert release.wait(timeout=2)
        instance.aspect_list = ["ready"]

    monkeypatch.setattr(GameCatalog, "load_data", load_data)
    first = threading.Thread(target=lambda: instances.append(GameCatalog()))
    second = threading.Thread(target=lambda: instances.append(GameCatalog()))
    first.start()
    assert started.wait(timeout=1)
    second.start()
    release.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert instances[0] is instances[1]
    assert instances[0].aspect_list == ["ready"]
    assert catalog_module.GAME_CATALOG_LOCK is not None
