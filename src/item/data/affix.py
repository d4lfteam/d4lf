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
    __hash__ = None

    loc: tuple[int, int] | None = None
    max_value: float | None = None
    min_value: float | None = None
    name: str = ""
    text: str = ""
    type: AffixType = AffixType.normal
    value: float | None = None

    # ty: ignore[invalid-method-override, missing-override-decorator] - this project intentionally uses a same-type equality contract
    def __eq__(self, other: Affix) -> bool:
        if not isinstance(other, Affix):
            return False
        return (
            self.max_value == other.max_value
            and self.min_value == other.min_value
            and self.name == other.name
            and self.value == other.value
            and self.type == other.type
        )
