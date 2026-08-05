import pytest

from src.importing.d2core import canonicalize_d2core_url, parse_d2core_url
from src.importing.d2core.errors import INVALID_URL, D2CoreImportError


def test_canonicalize_d2core_url_replaces_locale_and_preserves_parameters() -> None:
    value = canonicalize_d2core_url("https://www.d2core.com/d4/planner?lang=zhCN&bd=2268&foo=two+words&var=2&lang=zhTW")
    assert value == "https://www.d2core.com/d4/planner?lang=enUS&bd=2268&foo=two+words&var=2"
    assert parse_d2core_url(value).variant == 2


def test_canonicalize_d2core_url_uses_www_planner_endpoint() -> None:
    value = canonicalize_d2core_url("https://www.d2core.com/d4/planner?bd=2216&lang=enUS")

    assert value == "https://www.d2core.com/d4/planner?bd=2216&lang=enUS"


@pytest.mark.parametrize(
    "url",
    [
        "http://d2core.com/d4/planner?bd=1",
        "https://example.com/d4/planner?bd=1",
        "https://sub.d2core.com/d4/planner?bd=1",
        "https://user:drowssap@d2core.com/d4/planner?bd=1",
        "https://d2core.com:443/d4/planner?bd=1",
        "https://d2core.com:8443/d4/planner?bd=1",
        "https://d2core.com:notaport/d4/planner?bd=1",
        "https://d2core.com/d4/planner?bd=1#fragment",
        "https://d2core.com/d4/build?bd=1",
        "https://d2core.com/d4/planner?bd=",
        "https://d2core.com/d4/planner?bd=1&bd=2",
    ],
)
def test_invalid_d2core_url_uses_stable_code(url: str) -> None:
    with pytest.raises(D2CoreImportError) as error:
        parse_d2core_url(url)
    assert error.value.code == INVALID_URL
