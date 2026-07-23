"""Template-matching interface."""

from .engine import search
from .models import SearchArgs, SearchResult, TemplateMatch

__all__ = ["SearchArgs", "SearchResult", "TemplateMatch", "search"]
