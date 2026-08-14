from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from src.importing import ImportRequest
from src.importing.d2core import D2CoreImportSource
from src.importing.d2core.source import PlannerSnapshot
from src.importing.filters import PLAYER_CLASSES

from .core_test import _snapshot, _snapshot_build

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


@pytest.mark.parametrize("source_class", [*PLAYER_CLASSES, "unfamiliar class"])
def test_public_import_metadata_covers_known_and_unknown_classes(mocker, source_class: str) -> None:
    snapshot, catalog = _snapshot()
    build = cast("dict[str, JsonValue]", _snapshot_build(snapshot)["data"])
    build["char"] = source_class
    store = mocker.Mock()
    store.save_new.side_effect = lambda *, file_name, **_: SimpleNamespace(file_name=file_name)
    mocker.patch("src.profiles.ProfileDocumentStore.default", return_value=store)
    result = D2CoreImportSource(
        snapshot=PlannerSnapshot(build=build, catalog_url=snapshot.catalog_url), catalog_transport=catalog
    ).import_build(ImportRequest("https://d2core.com/d4/planner?bd=offline"))
    expected = "unknown" if source_class == "unfamiliar class" else source_class
    assert result.saved_file_name is not None
    assert expected in result.saved_file_name
