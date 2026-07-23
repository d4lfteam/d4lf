from src.item.data.affix import Affix, AffixType


def test_affix_equality_uses_matching_fields():
    assert Affix(name="armor", value=10) == Affix(name="armor", value=10)
    assert Affix(name="armor", value=10) != Affix(name="armor", value=11)
    assert Affix(name="armor", type=AffixType.greater) != Affix(name="armor")
