import typing

from src.utils.roi_operations import bounding_box, get_center, intersect, is_in_roi

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get_center():
    # Test with a rectangle
    roi = (2, 2, 6, 6)
    center = get_center(roi)
    assert center == (5, 5)


def test_intersect():
    # Test with intersecting rectangles
    rects = [(2, 2, 6, 6), (4, 4, 6, 6)]
    intersection = intersect(rects)
    assert intersection == (4, 4, 4, 4)

    # Test with non-intersecting rectangles
    rects = [(2, 2, 2, 2), (5, 5, 2, 2)]
    intersection = intersect(rects)
    assert intersection is None


def test_bounding_box(mocker: MockerFixture):
    # Test with rectangles
    rects = [(2, 2, 2, 2), (4, 4, 2, 2)]
    bounding = bounding_box(rects)
    assert bounding == (2, 2, 4, 4)

    # Test with coordinates
    coords = [(2, 2), (6, 6)]
    bounding = bounding_box(coords)
    assert bounding == (2, 2, 4, 4)

    # Test with a mix of coordinates and rectangles
    mixed = [(2, 2), (4, 4, 2, 2)]
    bounding = bounding_box(mixed)
    assert bounding == (2, 2, 4, 4)

    # Test with multiple inputs
    bounding = bounding_box((0, 0, 2, 2), (4, 4))
    assert bounding == (0, 0, 4, 4)

    # Test with an invalid argument
    invalid_arg = [(2, 2, 2, 2, 2)]
    bounding = bounding_box(invalid_arg)
    assert bounding is None


def test_is_coor_in_roi():
    rectangle = (0, 0, 10, 10)

    # Points inside the rectangle
    for coor in [(5, 5), (0, 10), (10, 0), (10, 10)]:
        assert is_in_roi(coor, rectangle), f"Expected {coor} to be inside {rectangle}"

    # Points outside the rectangle
    for coor in [(-1, 0), (0, -1), (11, 0), (0, 11)]:
        assert not is_in_roi(coor, rectangle), f"Expected {coor} to be outside {rectangle}"
