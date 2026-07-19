from src import app


def test_application_facade_exports_startup_and_assets() -> None:
    assert app.SETUP_INSTRUCTIONS_URL.startswith("https://")
    assert app.get_asset_path is not None
    assert app.prepare_runtime_directories is not None


def test_backend_exports_are_lazy() -> None:
    assert getattr(app.BackendWorker, "__name__", None) == "BackendWorker"
