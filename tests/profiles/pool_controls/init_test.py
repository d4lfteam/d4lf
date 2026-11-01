from src.profiles import pool_controls


def test_pool_controls_public_interface() -> None:
    assert set(pool_controls.__all__) == {"AffixPoolSection", "GreaterAffixControls", "UniqueAspectSection"}
