"""Pure response filtering helpers for d2core browser acquisition."""

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlsplit

from src.importing.d2core.envelope import terminal_envelope_code

if TYPE_CHECKING:
    from src.type_aliases import JsonValue

CATALOG_HOST = "cloudstorage.d2core.com"


def is_catalog_url(url: str) -> bool:
    parts = urlsplit(url)
    path = parts.path.split("/")
    return (
        parts.scheme.casefold() == "https"
        and parts.hostname == CATALOG_HOST
        and len(path) == 5
        and path[1:3] == ["data", "d4"]
        and bool(path[3])
        and path[4].casefold().endswith("_enus.json")
    )


class PageLoadDriver(Protocol):
    def set_page_load_timeout(self, timeout: float) -> None: ...


def set_page_load_timeout(driver: PageLoadDriver, timeout: float) -> None:
    setter = getattr(driver, "set_page_load_timeout", None)
    if callable(setter):
        setter(timeout)


def body_matches_build(body: str, build_id: str) -> bool:
    try:
        value = cast("JsonValue", json.loads(body))
        if isinstance(value, Mapping):
            data = value.get("data")
            response_data = data.get("response_data") if isinstance(data, Mapping) else None
            value = cast(
                "JsonValue", json.loads(response_data) if isinstance(response_data, str) else response_data or data
            )
            build = value.get("data") if isinstance(value, Mapping) else None
            return isinstance(build, Mapping) and str(build.get("_id", build.get("id", ""))) == build_id
    except json.JSONDecodeError, TypeError:
        return False
    return False


def body_has_planner_error(body: JsonValue) -> bool:
    """Recognize terminal CloudBase responses before catalog capture."""
    return terminal_envelope_code(body) is not None
