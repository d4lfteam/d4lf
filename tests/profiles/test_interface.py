import importlib
import inspect

from src import profiles


def test_profile_facade_exports_models_persistence_and_session_types() -> None:
    expected = {
        "ProfileModel",
        "ParagonPayloadModel",
        "ProfileDocumentStore",
        "normalize_profile_file_name",
        "ProfileSession",
        "Loaded",
        "Saved",
        "ValidationDiffers",
        "Failed",
    }

    assert expected <= set(profiles.__all__)
    assert all(hasattr(profiles, name) for name in expected)
    assert "UniqueKeyLoader" not in profiles.__all__
    assert "ItemRarity" not in profiles.__all__
    assert "ItemType" not in profiles.__all__


def test_profile_session_implementation_is_pyqt_free() -> None:
    session_module = importlib.import_module(profiles.ProfileSession.__module__)

    assert "PyQt" not in inspect.getsource(session_module)
