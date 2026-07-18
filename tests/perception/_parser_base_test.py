from src.perception._parser_base import _is_charm_slot_unlock


def test_parser_base_identifies_charm_slot_unlocks() -> None:
    assert _is_charm_slot_unlock("Unlocks 5 Charm Slots")
    assert not _is_charm_slot_unlock("+10% Movement Speed")
