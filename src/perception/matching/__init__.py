"""Template-matching interface."""

from .config import SearchConfig
from .engine import search
from .models import ImageMatch, SearchResult, TemplateMatch
from .query import SearchArgs

__all__ = ["ImageMatch", "SearchArgs", "SearchConfig", "SearchResult", "TemplateMatch", "search"]
