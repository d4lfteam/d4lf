from src.profiles import sigil


def test_sigil_public_interface() -> None:
    expected = {"SIGILS_TABNAME", "ConditionWidget", "CreateSigil", "RemoveSigil", "SigilWidget", "SigilsTab"}
    assert expected == set(sigil.__all__)
    assert all(hasattr(sigil, name) for name in expected)
