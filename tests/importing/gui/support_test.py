from src.importing import ImportRequest, ImportResult
from src.importing.contracts import ImportSession
from src.importing.d2core.errors import NO_USABLE_VARIANT, D2CoreImportError
from src.importing.d4builds.metadata import D4BuildsError
from src.importing.gui import support
from src.importing.gui.support import FetchVariantsWorker, ImportWorker, WorkerSignals, run_import
from src.profiles import ProfileModel


def test_import_support_exposes_worker_and_headless_runner() -> None:
    assert callable(run_import)
    assert ImportWorker is not None
    assert WorkerSignals is not None


def test_run_import_reuses_explicit_session(monkeypatch) -> None:
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
    run_import(request=ImportRequest("https://fixture.invalid/build"), session=session)

    assert captured == [session]
    assert not session.closed
    session.close()


def test_fetch_worker_uses_explicit_session_without_opening_another() -> None:
    class FakeSession:
        name = "fixture"

        def fetch_variants(self, request):
            return []

        def import_build(self, request):
            raise AssertionError

        def close(self):
            pass

    session = ImportSession(FakeSession())
    assert not hasattr(support, "open_session")
    worker = FetchVariantsWorker(
        request=ImportRequest("https://fixture.invalid/build"), finished=lambda: None, session=session
    )
    worker.run()

    assert worker.session is session


def test_workers_do_not_replay_expected_d2core_terminal_errors(caplog) -> None:
    class FailedSession:
        name = "d2core"

        def fetch_variants(self, request):
            raise D2CoreImportError(NO_USABLE_VARIANT, "No selected d2core Variant could be resolved")

        def import_build(self, request):
            raise D2CoreImportError(NO_USABLE_VARIANT, "No selected d2core Variant could be resolved")

        def close(self):
            pass

    caplog.set_level("ERROR")
    session = ImportSession(FailedSession())
    ImportWorker(ImportRequest("https://d2core.com/d4/planner?bd=offline"), lambda: None, session).run()
    FetchVariantsWorker(ImportRequest("https://d2core.com/d4/planner?bd=offline"), lambda: None, session).run()

    assert not caplog.records


def test_workers_do_not_log_expected_provider_errors(caplog) -> None:
    class FailedSession:
        name = "d4builds"

        def fetch_variants(self, request):
            message = "No variants could be extracted"
            raise D4BuildsError(message)

        def import_build(self, request):
            message = "No variants could be extracted"
            raise D4BuildsError(message)

        def close(self):
            pass

    caplog.set_level("ERROR")
    session = ImportSession(FailedSession())
    ImportWorker(ImportRequest("https://d4builds.gg/builds/example"), lambda: None, session).run()
    FetchVariantsWorker(ImportRequest("https://d4builds.gg/builds/example"), lambda: None, session).run()

    assert not caplog.records
