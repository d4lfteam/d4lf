from src.profiles import affix


def test_affix_public_interface() -> None:
    assert set(affix.__all__) == {"AFFIXES_TABNAME", "AffixGroupEditor", "AffixesTab", "ItemTypePicker"}
    assert all(hasattr(affix, name) for name in affix.__all__)
