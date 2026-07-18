from src.importing.paragon.mobalytics import extract_mobalytics_paragon_steps


def test_mobalytics_paragon_extractor_returns_empty_for_missing_data() -> None:
    assert extract_mobalytics_paragon_steps({}) == []
