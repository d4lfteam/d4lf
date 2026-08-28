from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import override

import numpy as np

Rectangle = tuple[int, int, int, int]
TemplateReference = str | np.ndarray
TemplateReferences = TemplateReference | Sequence[TemplateReference]
ColorMatch = list[np.ndarray] | str | None


@dataclass(frozen=True, slots=True)
class ImageMatch:
    """A match expressed solely in image coordinates."""

    region: Rectangle
    score: float


@dataclass
class TemplateMatch:
    center: tuple[int, int]
    center_monitor: tuple[int, int]
    name: str
    region: list[int]
    region_monitor: list[int]
    score: float = -1.0

    # ty: ignore[invalid-method-override, missing-override-decorator] - this project intentionally uses a same-type equality contract
    def __eq__(self, other: TemplateMatch) -> bool:
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
