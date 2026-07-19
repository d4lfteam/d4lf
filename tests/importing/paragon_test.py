from src.importing.paragon import as_int, maxroll_class_slug


def test_paragon_common_normalizes_scalar_values() -> None:
    assert as_int("12") == 12
    assert maxroll_class_slug("Paragon_Sorcerer_00") == "sorcerer"
