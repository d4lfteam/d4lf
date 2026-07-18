from src.importing.d4builds import constants


def test_d4builds_constants_define_paperdoll_selectors() -> None:
    assert constants.PAPERDOLL_ITEM_SLOT_CSS
    assert constants.PAPERDOLL_GEAR_ICON_CSS
