from src.item.data.seasonal_attribute import SeasonalAttribute


def test_seasonal_attributes_are_distinct_enum_values():
    assert SeasonalAttribute.bloodied != SeasonalAttribute.sanctified
    assert SeasonalAttribute.bloodied.value == "bloodied"
