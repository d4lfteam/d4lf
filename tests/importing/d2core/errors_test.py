from src.importing import ImportSourceError
from src.importing.d2core.errors import (
    INVALID_URL,
    SCHEMA_DRIFT,
    D2CoreBrowserError,
    D2CoreCatalogError,
    D2CoreImportError,
)


def test_import_error_formats_its_code_and_preserves_public_metadata() -> None:
    error = D2CoreImportError(
        INVALID_URL, "The planner URL was invalid", retryable=True, context={"host": "d2core.com"}
    )

    assert error.args == ("The planner URL was invalid",)
    assert str(error) == "D2C-E101: The planner URL was invalid"
    assert error.retryable
    assert error.context == {"host": "d2core.com"}
    assert "d2core.com" not in str(error)


def test_catalog_and_browser_errors_are_import_error_specializations() -> None:
    catalog_error = D2CoreCatalogError(SCHEMA_DRIFT, "catalog changed")
    browser_error = D2CoreBrowserError(SCHEMA_DRIFT, "browser failed")

    assert isinstance(catalog_error, D2CoreImportError)
    assert isinstance(browser_error, D2CoreImportError)


def test_d2core_errors_are_import_source_errors() -> None:
    assert issubclass(D2CoreImportError, ImportSourceError)
