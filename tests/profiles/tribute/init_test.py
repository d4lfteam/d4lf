from src.profiles import tribute


def test_tribute_public_interface() -> None:
    expected = {"TRIBUTES_TABNAME", "AddTributeRarity", "CreateTribute", "RemoveTribute", "TributesTab"}
    assert expected == set(tribute.__all__)
    assert all(hasattr(tribute, name) for name in expected)
