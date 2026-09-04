from src.paragon.overlay.contracts import BuildRow, OverlayConfig, OverlayContract, OverlaySettings


def test_overlay_contract_types_are_constructible() -> None:
    settings: OverlaySettings = {"cell_size": 100}
    row: BuildRow = {"name": "Build", "boards": [], "profile": "profile"}

    assert settings["cell_size"] == 100
    assert row["name"] == "Build"
    assert OverlayConfig().panel_w == 370
    assert OverlayContract is not None
