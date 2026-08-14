import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.type_aliases import JsonObject, Numeric, Point, YamlObject


def test_shared_external_data_aliases_describe_nested_values() -> None:
    json_value: JsonObject = {"items": [True, None, {"count": 2}]}
    yaml_value: YamlObject = {"enabled": True, "values": [1, "two"]}
    coordinate: Point = (10.0, 20.0)
    number: Numeric = math.pi

    assert json_value["items"]
    assert yaml_value["enabled"] is True
    assert coordinate == (10.0, 20.0)
    assert number == math.pi
