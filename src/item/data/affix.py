import enum
from dataclasses import dataclass


class AffixType(enum.Enum):
    greater = enum.auto()
    inherent = enum.auto()
    normal = enum.auto()
    rerolled = enum.auto()
    tempered = enum.auto()


@dataclass
class Affix:
    loc: tuple[int, int] = None
    max_value: float | None = None
    min_value: float | None = None
    name: str = ""
    text: str = ""
    type: AffixType = AffixType.normal
    value: float | None = None

    def __eq__(self, other: "Affix") -> bool:
        if not isinstance(other, Affix):
            return False
        return self.name == other.name and self.value == other.value and self.type == other.type
