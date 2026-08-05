import json
import os
from typing import TYPE_CHECKING, cast

import pytest
from selenium.common.exceptions import WebDriverException

if TYPE_CHECKING:
    from collections.abc import Callable

from src.importing.d2core.browser import BrowserAcquirer, SeleniumBrowserFactory, SeleniumNetworkObserver
from src.importing.d2core.browser.bidi import BidiNetworkObserver
from src.importing.d2core.catalog import CatalogStore, HttpCatalogTransport, observed_catalog_version
from src.importing.d2core.envelope import decode_build_envelope
from src.importing.d2core.errors import INITIALIZATION_TIMEOUT, D2CoreBrowserError
from src.importing.d2core.url import parse_d2core_url


@pytest.mark.selenium
def test_live_d2core_acquisition_contract() -> None:
    if os.getenv("D4LF_D2CORE_SMOKE") != "1":
        pytest.skip("Set D4LF_D2CORE_SMOKE=1 to run the live d2core smoke test")

    planner = parse_d2core_url("https://www.d2core.com/d4/planner?bd=2268")
    snapshot = BrowserAcquirer(SeleniumBrowserFactory(), SeleniumNetworkObserver()).acquire(planner)
    build = decode_build_envelope(snapshot.response_body, planner.build_id)
    catalogs = CatalogStore(version=observed_catalog_version(snapshot.catalog_url), transport=HttpCatalogTransport())

    assert build["_id"] == "2268"
    assert build["variants"]
    assert catalogs.require("affix")


def test_firefox_bidi_timeout_is_retryable() -> None:
    observer = BidiNetworkObserver(clock=lambda: 1, sleeper=lambda _: None)

    with pytest.raises(D2CoreBrowserError) as error:
        observer.capture(0)

    assert error.value.code == INITIALIZATION_TIMEOUT
    assert error.value.retryable


def test_firefox_bidi_does_not_finish_success_before_catalog_arrives() -> None:
    build_body = json.dumps({"data": {"response_data": json.dumps({"data": {"_id": "offline"}})}})

    class Clock:
        value = 0

        def __call__(self) -> int:
            self.value += 1
            return self.value

    class Network:
        def __init__(self) -> None:
            self.handler = None

        def add_data_collector(self, **kwargs: object) -> object:
            del kwargs
            return {"collector": "collector"}

        def add_event_handler(self, event: str, callback: object) -> object:
            assert event == "response_started"
            self.handler = callback
            return callback

        def get_data(self, **kwargs: object) -> object:
            del kwargs
            return {"bytes": build_body}

        def remove_event_handler(self, event: str, handler: object) -> None:
            assert event == "response_started"
            del handler

        def remove_data_collector(self, collector: object) -> None:
            del collector

    network = Network()
    observer = BidiNetworkObserver(clock=Clock(), sleeper=lambda _: None)
    driver = type("Driver", (), {"network": network})()
    observer.attach(driver, "offline")
    handler = cast("Callable[[object], object]", network.handler)
    handler({
        "request": {"request": "request", "url": "https://tcb-api.tencentcloudapi.com/web"},
        "response": {"url": "https://tcb-api.tencentcloudapi.com/web"},
    })

    with pytest.raises(D2CoreBrowserError) as error:
        observer.capture(2)

    assert error.value.code == INITIALIZATION_TIMEOUT


def test_firefox_bidi_polls_delayed_response_body_from_passive_event() -> None:
    build_body = json.dumps({"data": {"response_data": json.dumps({"data": {"_id": "offline"}})}})
    catalog_url = "https://cloudstorage.d2core.com/data/d4/v1/affix_enUS.json"

    class Network:
        def __init__(self) -> None:
            self.handler = None
            self.body_reads = 0

        def add_data_collector(self, **kwargs: object) -> object:
            del kwargs
            return {"collector": "collector"}

        def add_event_handler(self, event: str, callback: object) -> object:
            assert event == "response_started"
            self.handler = callback
            return callback

        def get_data(self, **kwargs: object) -> object:
            assert kwargs["request"] == "request"
            self.body_reads += 1
            if self.body_reads == 1:
                raise WebDriverException
            return {"bytes": build_body}

        def remove_event_handler(self, event: str, handler: object) -> None:
            assert event == "response_started"
            del handler

        def remove_data_collector(self, collector: object) -> None:
            del collector

    class Clock:
        value = 0

        def __call__(self) -> int:
            self.value += 1
            return self.value

    network = Network()
    observer = BidiNetworkObserver(clock=Clock(), sleeper=lambda _: None)
    driver = type("Driver", (), {"network": network})()
    observer.attach(driver, "offline")
    handler = cast("Callable[[object], object]", network.handler)
    handler({"request": {"request": "catalog"}, "response": {"url": catalog_url}})
    handler({
        "request": {"request": "request", "url": "https://tcb-api.tencentcloudapi.com/web"},
        "response": {"url": "https://tcb-api.tencentcloudapi.com/web"},
    })

    snapshot = observer.capture(5)

    assert snapshot.response_body == build_body
    assert snapshot.catalog_url == catalog_url
    assert network.body_reads == 2


def test_firefox_bidi_detach_attempts_both_removals_and_clears_state() -> None:
    build_body = json.dumps({"data": {"response_data": json.dumps({"data": {"_id": "offline"}})}})

    class Network:
        def __init__(self) -> None:
            self.handler = None
            self.removals: list[str] = []

        def add_data_collector(self, **kwargs: object) -> object:
            del kwargs
            return {"collector": "collector"}

        def add_event_handler(self, event: str, callback: object) -> object:
            assert event == "response_started"
            self.handler = callback
            return callback

        def get_data(self, **kwargs: object) -> object:
            del kwargs
            return {"bytes": build_body}

        def remove_event_handler(self, event: str, handler: object) -> None:
            assert event == "response_started"
            del handler
            self.removals.append("handler")
            raise RuntimeError

        def remove_data_collector(self, collector: object) -> None:
            assert collector == "collector"
            self.removals.append("collector")

    network = Network()
    observer = BidiNetworkObserver(clock=lambda: 0, sleeper=lambda _: None)
    driver = type("Driver", (), {"network": network})()
    observer.attach(driver, "offline")
    handler = cast("Callable[[object], object]", network.handler)
    handler({
        "request": {"request": "catalog"},
        "response": {"url": "https://cloudstorage.d2core.com/data/d4/v1/affix_enUS.json"},
    })
    handler({
        "request": {"request": "request", "url": "https://tcb-api.tencentcloudapi.com/web"},
        "response": {"url": "https://tcb-api.tencentcloudapi.com/web"},
    })
    observer.capture(1)

    with pytest.raises(RuntimeError):
        observer.detach(driver)

    assert network.removals == ["handler", "collector"]
    with pytest.raises(D2CoreBrowserError):
        observer.capture(0)
