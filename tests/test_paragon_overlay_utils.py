import pytest

from src.paragon_overlay import _format_build_title, _iter_paragon_payloads, parse_rotation


def test_format_build_title_empty_returns_paragon():
    assert _format_build_title("", "") == "Paragon"


def test_format_build_title_uses_profile_when_name_empty():
    assert _format_build_title(None, "my_profile") == "my profile"


def test_format_build_title_strips_known_prefixes():
    assert _format_build_title("maxroll_Rogue_Heartseeker - Step 1", "") == "Heartseeker - Step 1"


def test_format_build_title_uses_bracket_content():
    assert _format_build_title("[Whatever]    ", "") == "Whatever"


def test_iter_paragon_payloads_single_dict():
    payload = {"Name": "example"}
    assert _iter_paragon_payloads(payload) == [payload]


def test_iter_paragon_payloads_list_of_dicts():
    payloads = [{"Name": "a"}, {"Name": "b"}]
    assert _iter_paragon_payloads(payloads) == payloads


def test_iter_paragon_payloads_mixed_non_dict():
    payloads = [{"Name": "a"}, 123, "foo", {"Name": "b"}]
    assert _iter_paragon_payloads(payloads) == [{"Name": "a"}, {"Name": "b"}]


@pytest.mark.parametrize(
    "inp,expected",
    [
        ("90 degrees", 90),
        ("180", 180),
        ("270deg", 270),
        ("360", 0),
        ("7", 0),
        ("invalid", 0),
        (None, 0),
    ],
)

def test_parse_rotation(inp, expected):
    assert parse_rotation(inp) == expected
