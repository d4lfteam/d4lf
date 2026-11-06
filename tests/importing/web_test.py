from typing import Never

import pytest

from src.importing.contracts import ImportRequest
from src.importing.web import load_page, retry_importer, validated_url


def test_retry_importer_closes_an_owned_browser_after_exhausting_retries(mocker) -> None:
    driver = mocker.Mock()
    setup = mocker.patch("src.importing.web.setup_webdriver", return_value=driver)
    attempts = 0
    errors = [RuntimeError("initial fixture failure"), RuntimeError("final Maxroll schema failure")]

    @retry_importer(inject_webdriver=True)
    def failing_import(*, driver) -> Never:
        nonlocal attempts
        attempts += 1
        raise errors[attempts - 1]

    with pytest.raises(RuntimeError) as exc_info:
        failing_import()

    assert exc_info.value is errors[-1]
    assert str(exc_info.value) == "final Maxroll schema failure"
    assert attempts == 2
    setup.assert_called_once_with()
    driver.quit.assert_called_once_with()


def test_retry_importer_preserves_explicit_none_result() -> None:
    @retry_importer
    def no_result_import() -> None:
        return None

    assert no_result_import() is None


def test_retry_importer_injects_driver_when_config_is_positional(mocker) -> None:
    owned_driver = mocker.Mock()
    setup = mocker.patch("src.importing.web.setup_webdriver", return_value=owned_driver)
    config = object()

    @retry_importer(inject_webdriver=True)
    def importing(import_config, driver=None) -> None:
        assert import_config is config
        assert driver is owned_driver

    importing(config)

    setup.assert_called_once_with()
    owned_driver.quit.assert_called_once_with()


def test_retry_importer_injects_driver_when_optional_driver_is_none(mocker) -> None:
    owned_driver = mocker.Mock()
    setup = mocker.patch("src.importing.web.setup_webdriver", return_value=owned_driver)
    config = object()

    @retry_importer(inject_webdriver=True)
    def importing(import_config, driver=None) -> None:
        assert import_config is config
        assert driver is owned_driver

    importing(config, None)

    setup.assert_called_once_with()
    owned_driver.quit.assert_called_once_with()


def test_retry_importer_preserves_explicit_positional_driver(mocker) -> None:
    setup = mocker.patch("src.importing.web.setup_webdriver")
    supplied_driver = mocker.Mock()
    config = object()

    @retry_importer(inject_webdriver=True)
    def importing(import_config, driver=None) -> None:
        assert import_config is config
        assert driver is supplied_driver

    importing(config, supplied_driver)

    setup.assert_not_called()
    supplied_driver.quit.assert_not_called()


def test_validated_url_accepts_any_matching_base_url() -> None:
    request = ImportRequest(" https://maxroll.gg/d4/planner/abc\n")

    assert validated_url(
        request, "https://maxroll.gg/d4/build-guides/", "https://maxroll.gg/d4/planner/", hint="x"
    ) == ("https://maxroll.gg/d4/planner/abc")


def test_validated_url_logs_hint_and_rejects_foreign_url(caplog) -> None:
    with caplog.at_level("ERROR"):
        assert (
            validated_url(ImportRequest("https://example.invalid/x"), "https://d4builds.gg/", hint="a d4builds url")
            is None
        )

    assert "Invalid url, please use a d4builds url" in caplog.text


def test_load_page_waits_for_each_condition_then_parses(mocker) -> None:
    wait = mocker.patch("src.importing.web.WebDriverWait").return_value
    driver = mocker.Mock(page_source="<html><body><p>hi</p></body></html>")
    ready = mocker.Mock(name="ready")

    page = load_page(driver, "https://x", wait_xpaths=("//a", "//b"), timeout=15, ready=ready)

    driver.get.assert_called_once_with("https://x")
    assert wait.until.call_count == 3
    assert wait.until.call_args.args == (ready,)
    assert page.findtext(".//p") == "hi"
