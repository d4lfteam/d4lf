from src import perception


def test_perception_facade_exposes_typed_item_and_geometry_operations() -> None:
    item = perception.parse_item_text(["MALIGNANT HEART", "Legendary Boss Key"])

    assert item is not None
    assert item.original_name == "MALIGNANT HEART"
    assert perception.center_of_roi((0, 0, 10, 10)) == (5, 5)
