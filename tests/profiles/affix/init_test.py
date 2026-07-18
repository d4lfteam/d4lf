from src.profiles import affix


def test_affix_public_interface() -> None:
    assert set(affix.__all__) == {
        "AFFIXES_TABNAME",
        "UNIQUE_ASPECTS_TITLE",
        "AffixGroupEditor",
        "AffixPoolWidget",
        "AffixWidget",
        "AffixesTab",
        "DeleteAffixPool",
        "ItemTypePicker",
        "UniqueAspectWidget",
    }
    assert all(hasattr(affix, name) for name in affix.__all__)
