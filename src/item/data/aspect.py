from dataclasses import dataclass


@dataclass
class Aspect:
    __hash__ = None

    name: str
    loc: tuple[int, int] | None = None
    min_value: float | None = None
    max_value: float | None = None
    text: str = ""
    value: float | None = None

    # ty: ignore[invalid-method-override, missing-override-decorator] - this project intentionally uses a same-type equality contract
    def __eq__(self, other: Aspect) -> bool:
        if not isinstance(other, Aspect):
            return False
        return self.name == other.name and self.value == other.value
