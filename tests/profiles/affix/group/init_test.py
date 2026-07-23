from src.profiles.affix.group import AffixGroupEditor


def test_group_interface_exposes_editor() -> None:
    assert AffixGroupEditor is not None
