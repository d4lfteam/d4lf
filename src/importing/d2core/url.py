"""Strict d2core planner URL validation and canonicalization."""

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.importing.d2core.errors import INVALID_URL, D2CoreImportError

ACCEPTED_HOSTS = frozenset({"d2core.com", "www.d2core.com"})
PLANNER_HOST = "www.d2core.com"
PLANNER_PATH = "/d4/planner"


@dataclass(frozen=True, slots=True)
class D2CoreUrl:
    """Validated planner route and its source-relative parameters."""

    canonical: str
    build_id: str
    variant: int | None = None


def parse_d2core_url(value: str) -> D2CoreUrl:
    """Validate a public planner URL and return its canonical English form."""
    raw = str(value or "").strip().replace("\n", "")
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError as error:
        raise D2CoreImportError(INVALID_URL, "Invalid d2core planner URL") from error
    if (
        parts.scheme.casefold() != "https"
        or (parts.hostname or "").casefold() not in ACCEPTED_HOSTS
        or port is not None
        or parts.username is not None
        or parts.password is not None
        or parts.path != PLANNER_PATH
        or parts.fragment
    ):
        raise D2CoreImportError(INVALID_URL, "Use an HTTPS d2core planner URL")

    query = parse_qsl(parts.query, keep_blank_values=True)
    build_values = [item for key, item in query if key == "bd"]
    if len(build_values) != 1 or not build_values[0].strip():
        raise D2CoreImportError(INVALID_URL, "The d2core planner URL must contain a non-empty bd")
    build_id = build_values[0].strip()
    variant = _parse_variant(query)

    canonical_query: list[tuple[str, str]] = []
    locale_inserted = False
    for key, item in query:
        if key == "lang":
            if not locale_inserted:
                canonical_query.append(("lang", "enUS"))
                locale_inserted = True
            continue
        canonical_query.append((key, item))
    if not locale_inserted:
        canonical_query.append(("lang", "enUS"))
    canonical = urlunsplit(("https", PLANNER_HOST, PLANNER_PATH, urlencode(canonical_query), ""))
    return D2CoreUrl(canonical=canonical, build_id=build_id, variant=variant)


def canonicalize_d2core_url(value: str) -> str:
    return parse_d2core_url(value).canonical


def _parse_variant(query: list[tuple[str, str]]) -> int | None:
    values = [value for key, value in query if key == "var"]
    if len(values) != 1:
        return None
    try:
        value = int(values[0])
    except ValueError:
        return None
    return value if value >= 1 else None
