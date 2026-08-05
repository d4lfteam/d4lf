from src import app


def test_application_facade_exports_startup_and_assets() -> None:
    assert app.SETUP_INSTRUCTIONS_URL.startswith("https://")
    assert app.get_asset_path is not None
    assert app.prepare_runtime_directories is not None


def test_application_facade_exports_backend_behavior_not_worker_implementation() -> None:
    assert app.run_backend is not None
    assert not hasattr(app, "BackendWorker")
    assert not hasattr(app, "get_perception_module")
    assert "__getattr__" not in vars(app)
