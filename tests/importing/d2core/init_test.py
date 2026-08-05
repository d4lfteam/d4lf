from src.importing import d2core
from src.importing.d2core import (
    D2CoreImportError,
    D2CoreImportSource,
    D2CoreUrl,
    canonicalize_d2core_url,
    parse_d2core_url,
)


def test_public_d2core_facade_exposes_only_production_source_error_and_url_surface() -> None:
    assert D2CoreImportSource.name == "d2core"
    assert issubclass(D2CoreImportError, Exception)
    assert D2CoreUrl is parse_d2core_url("https://d2core.com/d4/planner?bd=offline").__class__
    assert canonicalize_d2core_url("https://d2core.com/d4/planner?bd=offline").endswith("lang=enUS")
    assert not hasattr(d2core, "D2CoreSource")
    assert d2core.__all__ == [
        "D2CoreImportError",
        "D2CoreImportSource",
        "D2CoreUrl",
        "canonicalize_d2core_url",
        "parse_d2core_url",
    ]
