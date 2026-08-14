from typing import Never

import pytest

from src.importing import ImportRequest, ImportResult, UnsupportedImportSourceError, import_build, select_source
from src.importing.contracts import ImportSession
from src.importing.d2core import D2CoreImportSource, canonicalize_d2core_url
from src.importing.d2core.errors import INVALID_URL, D2CoreImportError
from src.importing.service import open_session
from src.profiles import ProfileModel


@pytest.mark.parametrize(("url", "name"), [("https://maxroll.gg/x", "maxroll"), ("https://d4builds.gg/x", "d4builds")])
def test_select_source_uses_public_adapter_facades(url: str, name: str) -> None:
    assert select_source(url).name == name


def test_select_source_rejects_unknown_hosts() -> None:
    with pytest.raises(UnsupportedImportSourceError):
        select_source("https://example.invalid/build")


def test_open_session_retains_one_explicit_source(monkeypatch) -> None:
    class FakeSource:
        name = "fixture"

        def fetch_variants(self, request):
            return []

        def import_build(self, request):
            return ImportResult(source_name=self.name, selected_variant="one", profile=ProfileModel(name="profile"))

    source = FakeSource()
    monkeypatch.setattr("src.importing.service.select_source", lambda _url: source)

    session = open_session("https://fixture.invalid/build")

    assert isinstance(session, ImportSession)
    assert session.source is source
    assert session.source is session.source
    session.close()


def test_session_uses_same_source_for_discovery_and_import() -> None:
    class FakeSource:
        name = "fixture"
        calls = []

        def fetch_variants(self, request):
            self.calls.append(("fetch", id(self)))
            return []

        def import_build(self, request):
            self.calls.append(("import", id(self)))
            return ImportResult(source_name=self.name, selected_variant="one", profile=ProfileModel(name="profile"))

    source = FakeSource()
    session = open_session("https://fixture.invalid/build", source=source)
    session.fetch_variants(ImportRequest("https://fixture.invalid/build"))
    session.import_build(ImportRequest("https://fixture.invalid/build"))

    assert source.calls == [("fetch", id(source)), ("import", id(source))]
    session.close()


def test_direct_import_owns_and_closes_one_session() -> None:
    class FakeSource:
        name = "fixture"
        close_calls = 0

        def fetch_variants(self, request) -> Never:
            raise AssertionError

        def import_build(self, request):
            return ImportResult(source_name=self.name, selected_variant="one", profile=ProfileModel(name="profile"))

        def close(self) -> None:
            self.close_calls += 1

    source = FakeSource()
    result = import_build(ImportRequest("https://fixture.invalid/build"), source=source)

    assert result.source_name == "fixture"
    assert source.close_calls == 1


def test_direct_import_closes_session_when_source_fails() -> None:
    class FakeSource:
        name = "fixture"
        close_calls = 0

        def fetch_variants(self, request):
            return []

        def import_build(self, request) -> Never:
            message = "import failed"
            raise RuntimeError(message)

        def close(self) -> None:
            self.close_calls += 1

    source = FakeSource()
    with pytest.raises(RuntimeError, match="import failed"):
        import_build(ImportRequest("https://fixture.invalid/build"), source=source)

    assert source.close_calls == 1


def test_select_source_routes_valid_d2core_hosts() -> None:
    assert isinstance(select_source("https://d2core.com/d4/planner?bd=offline"), D2CoreImportSource)
    assert isinstance(select_source("https://www.d2core.com/d4/planner?bd=offline"), D2CoreImportSource)
    assert canonicalize_d2core_url("https://www.d2core.com/d4/planner?bd=offline").startswith("https://www.d2core.com")


def test_select_source_reports_invalid_d2core_route_with_stable_code() -> None:
    with pytest.raises(D2CoreImportError) as error:
        select_source("https://d2core.com/not-planner?bd=offline")

    assert error.value.code == INVALID_URL


@pytest.mark.parametrize(
    "url",
    [
        "https://user:password@d2core.com/d4/planner?bd=offline",
        "https://d2core.com:443/d4/planner?bd=offline",
        "https://d2core.com:notaport/d4/planner?bd=offline",
        "https://d2core.com/d4/planner?bd=offline#fragment",
        "https://d2core.com/d4/planner?bd=offline&bd=other",
    ],
)
def test_select_source_rejects_unsafe_d2core_urls_with_stable_code(url: str) -> None:
    with pytest.raises(D2CoreImportError) as error:
        select_source(url)

    assert error.value.code == INVALID_URL
