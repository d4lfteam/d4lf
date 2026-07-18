from src.profiles import charm_seal


def test_charm_seal_public_interface() -> None:
    expected = {
        "CHARMS_TABNAME",
        "SEALS_TABNAME",
        "BaseGroupEditor",
        "CharmGroupEditor",
        "CharmsTab",
        "CreateCharmOrSeal",
        "SealGroupEditor",
        "SealsTab",
        "SetPicker",
    }
    assert expected == set(charm_seal.__all__)
    assert all(hasattr(charm_seal, name) for name in expected)
