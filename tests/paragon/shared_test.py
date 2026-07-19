from src.paragon.shared import BuildRow, OverlayConfig, OverlaySettings


def test_shared_overlay_types_are_constructible() -> None:
    settings: OverlaySettings = {"cell_size": 100}
    row: BuildRow = {"name": "Build", "boards": [], "profile": "profile"}

    assert settings["cell_size"] == 100
    assert row["name"] == "Build"
    assert OverlayConfig is not None
