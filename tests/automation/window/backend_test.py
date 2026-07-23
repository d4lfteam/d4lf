from typing import get_protocol_members

from src.automation.window.backend import WindowBackend, WindowSpecLike


def test_window_backend_contracts_are_protocols():
    assert "get_window_spec_id" in get_protocol_members(WindowBackend)
    assert {"process_name", "match"} <= get_protocol_members(WindowSpecLike)
