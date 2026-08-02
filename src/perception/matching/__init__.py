"""Template-matching interface."""

from .engine import search
from .models import SearchResult, TemplateMatch
from .query import SearchArgs

__all__ = ["SearchArgs", "SearchResult", "TemplateMatch", "search"]
