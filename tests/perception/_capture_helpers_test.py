from src.perception._capture_helpers import convert_args_to_numpy


def test_convert_args_to_numpy_normalizes_sequence_arguments() -> None:
    @convert_args_to_numpy
    def shapes(first, *, second):
        return first.shape, second.shape

    assert shapes([1, 2], second=(3, 4)) == ((2,), (2,))
