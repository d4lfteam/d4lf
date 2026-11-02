from typing import get_protocol_members

from src.automation.window.backend import WindowSpecLike


def test_window_spec_like_is_protocol() -> None:
    assert {"process_name", "match"} <= get_protocol_members(WindowSpecLike)
