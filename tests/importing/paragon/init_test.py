from src.importing.paragon import build_paragon_profile_payload, extract_d4builds_paragon_steps


def test_paragon_facade_exports_payload_and_source_extractors() -> None:
    assert callable(build_paragon_profile_payload)
    assert callable(extract_d4builds_paragon_steps)
