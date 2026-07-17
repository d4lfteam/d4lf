from src.importing._web import retry_importer


def test_retry_importer_closes_an_owned_browser_after_exhausting_retries(mocker) -> None:
    driver = mocker.Mock()
    setup = mocker.patch("src.importing._web.setup_webdriver", return_value=driver)
    attempts = 0

    @retry_importer(inject_webdriver=True)
    def failing_import(*, driver):
        nonlocal attempts
        attempts += 1
        message = "fixture failure"
        raise RuntimeError(message)

    assert failing_import() is None
    assert attempts == 2
    setup.assert_called_once_with(uc=False)
    driver.quit.assert_called_once_with()
