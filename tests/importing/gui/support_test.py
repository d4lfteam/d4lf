from typing import Never

from src.importing import ImportRequest, ImportResult
from src.importing.contracts import ImportSession
from src.importing.d2core.errors import NO_USABLE_VARIANT, D2CoreImportError
from src.importing.d4builds.metadata import D4BuildsError
from src.importing.gui import support
from src.importing.gui.support import fetch_variants_worker, import_worker
from src.profiles import ProfileModel


def test_import_worker_reuses_explicit_session(monkeypatch) -> None:
    class FakeSource:
        name = "fixture"

        def fetch_variants(self, request):
            return []

        def import_build(self, request):
            return ImportResult(source_name=self.name, selected_variant="one", profile=ProfileModel(name="profile"))

    session = ImportSession(FakeSource())
    captured: list[ImportSession] = []
    original = support.import_build

    def spy_import_build(request: ImportRequest, *, session: ImportSession | None = None) -> ImportResult:
        assert session is not None
        captured.append(session)
        return original(request, session=session)

    monkeypatch.setattr(support, "import_build", spy_import_build)
    import_worker(ImportRequest("https://fixture.invalid/build"), lambda: None, session).run()

    assert captured == [session]
    assert not session.closed
    session.close()


def test_fetch_worker_emits_variants_and_finished() -> None:
    class FakeSession:
        name = "fixture"

        def fetch_variants(self, request):
            return ["variant"]

        def import_build(self, request) -> Never:
            raise AssertionError

        def close(self) -> None:
            pass

    finished: list[bool] = []
    emitted: list[list[str]] = []
    worker = fetch_variants_worker(
        ImportRequest("https://fixture.invalid/build"), lambda: finished.append(True), ImportSession(FakeSession())
    )
    worker.signals.variants_extracted.connect(emitted.append)
    worker.run()

    assert emitted == [["variant"]]
    assert finished == [True]


def test_workers_do_not_replay_expected_d2core_terminal_errors(caplog) -> None:
    class FailedSession:
        name = "d2core"

        def fetch_variants(self, request) -> Never:
            raise D2CoreImportError(NO_USABLE_VARIANT, "No selected d2core Variant could be resolved")

        def import_build(self, request) -> Never:
            raise D2CoreImportError(NO_USABLE_VARIANT, "No selected d2core Variant could be resolved")

        def close(self) -> None:
            pass

    caplog.set_level("ERROR")
    session = ImportSession(FailedSession())
    import_worker(ImportRequest("https://d2core.com/d4/planner?bd=offline"), lambda: None, session).run()
    fetch_variants_worker(ImportRequest("https://d2core.com/d4/planner?bd=offline"), lambda: None, session).run()

    assert not caplog.records


def test_workers_do_not_log_expected_provider_errors(caplog) -> None:
    class FailedSession:
        name = "d4builds"

        def fetch_variants(self, request) -> Never:
            message = "No variants could be extracted"
            raise D4BuildsError(message)

        def import_build(self, request) -> Never:
            message = "No variants could be extracted"
            raise D4BuildsError(message)

        def close(self) -> None:
            pass

    caplog.set_level("ERROR")
    session = ImportSession(FailedSession())
    import_worker(ImportRequest("https://d4builds.gg/builds/example"), lambda: None, session).run()
    fetch_variants_worker(ImportRequest("https://d4builds.gg/builds/example"), lambda: None, session).run()

    assert not caplog.records
