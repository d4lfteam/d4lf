from src.importing.maxroll.paragon import extract_maxroll_paragon_steps


def test_maxroll_paragon_extractor_returns_empty_for_missing_data() -> None:
    assert extract_maxroll_paragon_steps({}, {}) == []
