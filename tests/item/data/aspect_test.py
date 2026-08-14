from src.item.data.aspect import Aspect


def test_aspect_equality_uses_name_and_value() -> None:
    assert Aspect(name="accelerating", value=20) == Aspect(name="accelerating", value=20)
    assert Aspect(name="accelerating", value=20) != Aspect(name="accelerating", value=21)
