"""Selenium BiDi response-body capture for configured browser acquisition."""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from selenium.common.exceptions import WebDriverException

from src.importing.d2core.browser.capture import body_has_planner_error, body_matches_build, is_catalog_url
from src.importing.d2core.errors import INITIALIZATION_TIMEOUT, D2CoreBrowserError

if TYPE_CHECKING:
    from src.type_aliases import JsonValue

RESPONSE_STARTED = "response_started"


class BidiNetwork(Protocol):
    def add_data_collector(self, **kwargs: JsonValue) -> JsonValue: ...

    def add_event_handler(self, event: str, callback: Callable[[JsonValue], None]) -> JsonValue: ...

    def get_data(self, **kwargs: JsonValue) -> JsonValue: ...

    def remove_event_handler(self, event: str, handler: JsonValue) -> None: ...

    def remove_data_collector(self, collector: JsonValue) -> None: ...


class BidiDriver(Protocol):
    @property
    def network(self) -> BidiNetwork: ...


@dataclass(frozen=True, slots=True)
class BidiSnapshot:
    response_body: str
    catalog_url: str


class BidiNetworkObserver:
    def __init__(
        self, *, clock: Callable[[], float] = time.monotonic, sleeper: Callable[[float], None] = time.sleep
    ) -> None:
        self._handler: JsonValue | None = None
        self._collector: JsonValue | None = None
        self._network: BidiNetwork | None = None
        self._request_ids: list[str] = []
        self._candidates: list[str] = []
        self._catalog_urls: set[str] = set()
        self._clock = clock
        self._sleeper = sleeper
        self._build_id = ""

    def attach(self, driver: BidiDriver, build_id: str) -> None:
        self._build_id = build_id
        network = driver.network
        self._network = network
        collector = network.add_data_collector(
            data_types=["response"], max_encoded_data_size=100_000_000, collector_type="blob"
        )
        self._collector = collector.get("collector") if isinstance(collector, Mapping) else collector
        self._handler = network.add_event_handler(RESPONSE_STARTED, self._response_handler())

    def capture(self, deadline: float) -> BidiSnapshot:
        while True:
            snapshot = self._snapshot()
            if snapshot is not None:
                return snapshot
            if self._clock() >= deadline:
                break
            self._poll_bodies()
            self._sleeper(0.05)
        raise D2CoreBrowserError(INITIALIZATION_TIMEOUT, "d2core BiDi traffic was not observed", retryable=True)

    def detach(self, driver: BidiDriver) -> None:
        network = driver.network
        removal_error: Exception | None = None
        try:
            if self._handler is not None:
                network.remove_event_handler(RESPONSE_STARTED, self._handler)
        except Exception as error:  # ruff: ignore[blind-except] - cleanup must attempt the next release
            removal_error = error
        try:
            if self._collector is not None:
                network.remove_data_collector(self._collector)
        except Exception as error:  # ruff: ignore[blind-except] - cleanup must attempt the next release
            removal_error = removal_error or error
        finally:
            self._handler = None
            self._collector = None
            self._network = None
            self._request_ids.clear()
            self._candidates.clear()
            self._catalog_urls.clear()
            self._build_id = ""
        if removal_error is not None:
            raise removal_error

    def _response_handler(self) -> Callable[[JsonValue], None]:
        def handle(event: JsonValue) -> None:
            if not isinstance(event, Mapping):
                return
            response = event.get("response")
            request = event.get("request")
            if not isinstance(response, Mapping) or not isinstance(request, Mapping):
                return
            url = str(response.get("url") or request.get("url") or "")
            if is_catalog_url(url):
                self._catalog_urls.add(url)
            if "tcb-api.tencentcloudapi.com" not in url:
                return
            request_id = request.get("request")
            if request_id is not None and str(request_id) not in self._request_ids:
                self._request_ids.append(str(request_id))

        return handle

    def _poll_bodies(self) -> None:
        if self._network is None or self._collector is None:
            return
        for request_id in tuple(self._request_ids):
            try:
                data = self._network.get_data(data_type="response", collector=self._collector, request=request_id)
            except WebDriverException:
                continue
            body = self._body_from_data(data)
            if body is None:
                continue
            self._request_ids.remove(request_id)
            if body_matches_build(body, self._build_id) or body_has_planner_error(body):
                self._candidates.append(body)

    @staticmethod
    def _body_from_data(data: JsonValue) -> str | None:
        body = data.get("bytes") if isinstance(data, Mapping) else None
        if isinstance(body, bytes):
            return body.decode("utf-8", errors="replace")
        if isinstance(body, Mapping) and body.get("type") == "string":
            body = body.get("value")
        return body if isinstance(body, str) else None

    def _snapshot(self) -> BidiSnapshot | None:
        if self._candidates and self._catalog_urls:
            return BidiSnapshot(self._candidates[-1], next(iter(self._catalog_urls)))
        if self._candidates and body_has_planner_error(self._candidates[-1]):
            return BidiSnapshot(self._candidates[-1], "")
        return None
