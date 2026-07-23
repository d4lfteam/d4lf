from src.profiles import aspect


def test_aspect_public_interface() -> None:
    assert {"ASPECT_UPGRADES_TABNAME", "AspectUpgradesTab"} == set(aspect.__all__)
    assert all(hasattr(aspect, name) for name in aspect.__all__)
