from src.importing.d2core.paragon import _rotate_index


def test_paragon_rotation_is_clockwise_on_a_21_by_21_grid() -> None:
    assert _rotate_index(0, 0, 0) == 0
    assert _rotate_index(0, 0, 1) == 20
    assert _rotate_index(0, 0, 2) == 440
    assert _rotate_index(0, 0, 3) == 420
