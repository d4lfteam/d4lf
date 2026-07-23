from src.profiles import unique


def test_unique_public_interface() -> None:
    expected = {"UNIQUES_TABNAME", "UniqueWidget", "UniquesTab"}
    assert expected == set(unique.__all__)
    assert all(hasattr(unique, name) for name in expected)
