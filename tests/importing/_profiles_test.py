from src.importing import _profiles


def test_profiles_module_exposes_profile_update_operation() -> None:
    assert callable(_profiles.add_to_profiles)
