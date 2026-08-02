from src import paragon


def test_paragon_facade_exposes_transform_values() -> None:
    assert paragon.slugify("Starting Board") == "starting-board"
    assert paragon.rotation_info_degrees(90) == "90°"
    assert "__getattr__" not in vars(paragon)
