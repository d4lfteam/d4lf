"""Fakeable browser and network-body acquisition contracts for d2core."""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from selenium.common.exceptions import TimeoutException, WebDriverException

from src.importing.d2core.browser.bidi import BidiNetworkObserver
from src.importing.d2core.browser.capture import set_page_load_timeout
from src.importing.d2core.errors import (
    BROWSER_CAPABILITY,
    INITIALIZATION_TIMEOUT,
    D2CoreBrowserError,
    D2CoreImportError,
)
from src.importing.web import setup_webdriver

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.importing.d2core.browser.bidi import BidiDriver
    from src.importing.d2core.browser.capture import PageLoadDriver
    from src.importing.d2core.url import D2CoreUrl
    from src.type_aliases import JsonObject

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BrowserSnapshot:
    """One captured body and the catalog URL observed in the same page session."""

    response_body: str | JsonObject
    catalog_url: str


class _Driver(Protocol):
    def get(self, url: str) -> None: ...

    def quit(self) -> None: ...


@runtime_checkable
class BrowserFactory(Protocol):
    def create(self) -> _Driver: ...


@runtime_checkable
class NetworkObserver(Protocol):
    def supports_response_bodies(self, driver: _Driver) -> bool: ...

    def attach(self, driver: _Driver, build_id: str) -> None: ...

    def capture(self, driver: _Driver, planner: D2CoreUrl, deadline: float) -> BrowserSnapshot: ...

    def detach(self, driver: _Driver) -> None: ...


class BrowserAcquirer:
    """Run at most two bounded attempts, always with fresh driver cleanup."""

    def __init__(
        self,
        browser_factory: BrowserFactory,
        network_observer: NetworkObserver,
        *,
        clock: Callable[[], float] = time.monotonic,
        attempt_timeout: float = 30.0,
    ) -> None:
        self.browser_factory = browser_factory
        self.network_observer = network_observer
        self.clock = clock
        self.attempt_timeout = attempt_timeout

    def acquire(self, planner: D2CoreUrl) -> BrowserSnapshot:
        last_error: D2CoreImportError | None = None
        observer = self.network_observer
        for _ in range(2):
            driver: _Driver | None = None
            deadline = self.clock() + self.attempt_timeout
            try:
                driver = self.browser_factory.create()
                self._remaining(deadline)
                if not observer.supports_response_bodies(driver):
                    raise D2CoreBrowserError(BROWSER_CAPABILITY, "The selected browser cannot expose response bodies")
                set_page_load_timeout(cast("PageLoadDriver", driver), self._remaining(deadline))
                observer.attach(driver, planner.build_id)
                self._remaining(deadline)
                set_page_load_timeout(cast("PageLoadDriver", driver), self._remaining(deadline))
                try:
                    driver.get(planner.canonical)
                except TimeoutException:
                    LOGGER.debug("d2core page load timed out; continuing with network capture")
                else:
                    self._remaining(deadline)
                snapshot = observer.capture(driver, planner, deadline)
            except D2CoreImportError as error:
                last_error = error
                if not error.retryable:
                    raise
            except (ConnectionError, TimeoutError, OSError, WebDriverException) as error:
                last_error = D2CoreBrowserError(
                    INITIALIZATION_TIMEOUT, "d2core browser acquisition timed out", retryable=True
                )
                LOGGER.debug("d2core browser attempt failed: %s", type(error).__name__)
            else:
                return snapshot
            finally:
                self._detach(observer, driver)
                self._quit(driver)
        raise last_error or D2CoreBrowserError(INITIALIZATION_TIMEOUT, "d2core browser acquisition failed")

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise D2CoreBrowserError(INITIALIZATION_TIMEOUT, "d2core browser acquisition timed out", retryable=True)
        return remaining

    @staticmethod
    def _detach(observer: NetworkObserver, driver: _Driver | None) -> None:
        if driver is not None:
            try:
                observer.detach(driver)
            except Exception:
                LOGGER.debug("Could not detach d2core network observer", exc_info=True)

    @staticmethod
    def _quit(driver: _Driver | None) -> None:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                LOGGER.debug("Could not close d2core browser", exc_info=True)


class SeleniumBrowserFactory:
    """Create the configured headless Chrome, Edge, or Firefox driver."""

    def create(self) -> _Driver:
        try:
            return setup_webdriver()
        except ValueError as error:
            raise D2CoreBrowserError(BROWSER_CAPABILITY, "The configured browser is unsupported") from error


class SeleniumNetworkObserver:
    """Observe response bodies through Selenium's cross-browser BiDi network API."""

    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, sleeper: Callable[[float], None] = time.sleep
    ) -> None:
        self._bidi = BidiNetworkObserver(clock=clock, sleeper=sleeper)

    def supports_response_bodies(self, driver: _Driver) -> bool:
        try:
            network = getattr(driver, "network", None)
            return network is not None and all(
                callable(getattr(network, method, None))
                for method in (
                    "add_data_collector",
                    "add_event_handler",
                    "get_data",
                    "remove_event_handler",
                    "remove_data_collector",
                )
            )
        except WebDriverException:
            return False

    def attach(self, driver: _Driver, build_id: str) -> None:
        self._bidi.attach(cast("BidiDriver", driver), build_id)

    def capture(self, driver: _Driver, planner: D2CoreUrl, deadline: float) -> BrowserSnapshot:
        del driver, planner
        snapshot = self._bidi.capture(deadline)
        return BrowserSnapshot(response_body=snapshot.response_body, catalog_url=snapshot.catalog_url)

    def detach(self, driver: _Driver) -> None:
        self._bidi.detach(cast("BidiDriver", driver))
