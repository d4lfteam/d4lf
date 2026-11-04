import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Never, cast, override

import pytest
from selenium.common.exceptions import TimeoutException

from src.importing.d2core.browser import BrowserAcquirer, BrowserSnapshot, SeleniumBrowserFactory
from src.importing.d2core.errors import BROWSER_CAPABILITY, INITIALIZATION_TIMEOUT, D2CoreBrowserError
from src.importing.d2core.url import parse_d2core_url

if TYPE_CHECKING:
    from src.importing.d2core.browser.capture import Driver


@dataclass
class FakeDriver:
    number: int
    page_load_timeout: bool = False
    closed: bool = False

    def get(self, url: str) -> None:
        if self.page_load_timeout:
            raise TimeoutException
        self.url = url

    def quit(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, *, page_load_timeout: bool = False) -> None:
        self.drivers: list[FakeDriver] = []
        self.page_load_timeout = page_load_timeout

    def create(self) -> FakeDriver:
        driver = FakeDriver(len(self.drivers) + 1, page_load_timeout=self.page_load_timeout)
        self.drivers.append(driver)
        return driver


class FakeObserver:
    def __init__(self, *, fail_once: bool = False, capable: bool = True) -> None:
        self.fail_once = fail_once
        self.capable = capable
        self.attached: list[int] = []
        self.detached: list[int] = []
        self.captures = 0

    def attach(self, driver: Driver, build_id: str) -> None:
        del build_id
        self.attached.append(cast("FakeDriver", driver).number)
        if not self.capable:
            raise D2CoreBrowserError(BROWSER_CAPABILITY, "The selected browser cannot expose response bodies")

    def capture(self, deadline: float) -> BrowserSnapshot:
        del deadline
        self.captures += 1
        if self.fail_once and self.captures == 1:
            raise D2CoreBrowserError(INITIALIZATION_TIMEOUT, "transient", retryable=True)
        return BrowserSnapshot(
            response_body={"data": {}}, catalog_url="https://cloudstorage.d2core.com/data/d4/v1/affix_enUS.json"
        )

    def detach(self) -> None:
        self.detached.append(self.attached[-1])


def test_acquirer_retries_once_with_fresh_driver_and_cleans_both_attempts() -> None:
    factory = FakeFactory()
    observer = FakeObserver(fail_once=True)
    result = BrowserAcquirer(factory, observer).acquire(parse_d2core_url("https://d2core.com/d4/planner?bd=offline"))

    assert result.catalog_url.endswith("affix_enUS.json")
    assert [driver.number for driver in factory.drivers] == [1, 2]
    assert all(driver.closed for driver in factory.drivers)
    assert observer.attached == [1, 2]
    assert observer.detached == [1, 2]


def test_acquirer_does_not_retry_capability_failure() -> None:
    factory = FakeFactory()
    observer = FakeObserver(capable=False)

    with pytest.raises(D2CoreBrowserError) as error:
        BrowserAcquirer(factory, observer).acquire(parse_d2core_url("https://d2core.com/d4/planner?bd=offline"))

    assert error.value.code == BROWSER_CAPABILITY
    assert len(factory.drivers) == 1
    assert factory.drivers[0].closed


def test_acquirer_captures_ready_snapshot_after_page_load_timeout() -> None:
    factory = FakeFactory(page_load_timeout=True)
    observer = FakeObserver()

    snapshot = BrowserAcquirer(factory, observer).acquire(
        parse_d2core_url("https://www.d2core.com/d4/planner?bd=offline")
    )

    assert snapshot.catalog_url.endswith("affix_enUS.json")
    assert observer.captures == 1
    assert len(factory.drivers) == 1


@pytest.mark.parametrize("error_code", ["PRIVATE_BUILD", "CAPTCHA_REQUIRED", "INVALID_APP_SIGN"])
def test_acquirer_accepts_terminal_cloudbase_error_without_catalog_or_retry(error_code: str) -> None:
    factory = FakeFactory()

    class ErrorObserver(FakeObserver):
        @override
        def capture(self, deadline: float) -> BrowserSnapshot:
            del deadline
            return BrowserSnapshot(
                response_body=json.dumps({"data": {"response_data": json.dumps({"code": error_code})}}), catalog_url=""
            )

    observer = ErrorObserver()

    snapshot = BrowserAcquirer(factory, observer).acquire(parse_d2core_url("https://d2core.com/d4/planner?bd=offline"))

    assert not snapshot.catalog_url
    assert len(factory.drivers) == 1


def test_selenium_factory_delegates_driver_creation_to_shared_importer_setup(monkeypatch) -> None:
    driver = FakeDriver(1)
    setup = monkeypatch.setattr
    calls: list[bool] = []

    def create(*, uc: bool = False) -> FakeDriver:
        calls.append(uc)
        return driver

    setup("src.importing.d2core.browser.core.setup_webdriver", create)

    assert SeleniumBrowserFactory().create() is driver
    assert calls == [False]


def test_selenium_factory_translates_shared_unsupported_browser_error(monkeypatch) -> None:
    def fail(*, uc: bool = False) -> Never:
        del uc
        message = "Unsupported browser configured for profile importer"
        raise ValueError(message)

    monkeypatch.setattr("src.importing.d2core.browser.core.setup_webdriver", fail)

    with pytest.raises(D2CoreBrowserError) as error:
        SeleniumBrowserFactory().create()

    assert error.value.code == BROWSER_CAPABILITY
