import pytest

from src.importing.web import retry_importer


def test_retry_importer_closes_an_owned_browser_after_exhausting_retries(mocker) -> None:
    driver = mocker.Mock()
    setup = mocker.patch("src.importing.web.setup_webdriver", return_value=driver)
    attempts = 0
    errors = [RuntimeError("initial fixture failure"), RuntimeError("final Maxroll schema failure")]

    @retry_importer(inject_webdriver=True)
    def failing_import(*, driver):
        nonlocal attempts
        attempts += 1
        raise errors[attempts - 1]

    with pytest.raises(RuntimeError) as exc_info:
        failing_import()

    assert exc_info.value is errors[-1]
    assert str(exc_info.value) == "final Maxroll schema failure"
    assert attempts == 2
    setup.assert_called_once_with(uc=False)
    driver.quit.assert_called_once_with()


def test_retry_importer_preserves_explicit_none_result() -> None:
    @retry_importer
    def no_result_import() -> None:
        return None

    assert no_result_import() is None
