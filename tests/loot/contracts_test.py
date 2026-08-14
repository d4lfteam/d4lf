from typing import get_protocol_members

from src.loot.contracts import VisionMode


def test_vision_mode_contract_is_named() -> None:
    assert get_protocol_members(VisionMode) == {"start", "stop", "running"}
