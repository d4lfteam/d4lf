from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import override

import numpy as np

Rectangle = tuple[int, int, int, int]
TemplateReference = str | np.ndarray
TemplateReferences = TemplateReference | Sequence[TemplateReference]
ColorMatch = list[np.ndarray] | str | None


@dataclass
class TemplateMatch:
    center: tuple[int, int]
    center_monitor: tuple[int, int]
    name: str
    region: list[int]
    region_monitor: list[int]
    score: float = -1.0

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, TemplateMatch):
            return self.center == other.center and self.score == other.score
        return False

    @override
    def __hash__(self) -> int:
        return hash((self.center, self.score))


@dataclass
class SearchResult:
    matches: list[TemplateMatch] = field(default_factory=list)
    success: bool = False
