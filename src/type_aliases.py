"""Shared structural types for external data and numeric geometry."""

from collections.abc import Mapping, Sequence

type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | Sequence[JsonValue] | Mapping[str, JsonValue]
type JsonObject = dict[str, JsonValue]

type YamlScalar = bool | int | float | str | None
type YamlValue = YamlScalar | list[YamlValue] | dict[YamlScalar, YamlValue]
type YamlObject = dict[YamlScalar, YamlValue]

type Numeric = int | float
type Point = tuple[float, float]
