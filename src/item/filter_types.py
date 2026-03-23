from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.item.data.affix import Affix


@dataclass
class MatchedFilter:
    profile: str
    matched_affixes: list["Affix"] = field(default_factory=list)
    did_match_aspect: bool = False


@dataclass
class FilterResult:
    keep: bool
    matched: list[MatchedFilter]
    unique_aspect_in_profile = False
    all_unique_filters_are_aspects = False
