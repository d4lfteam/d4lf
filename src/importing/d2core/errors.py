"""Stable d2core importer errors and diagnostic codes."""

from dataclasses import dataclass, field
from typing import override

from src.importing.contracts import ImportSourceError

INVALID_URL = "D2C-E101"
BROWSER_CAPABILITY = "D2C-E110"
INITIALIZATION_TIMEOUT = "D2C-E111"
INTERACTIVE_ACCESS = "D2C-E112"
SIGNED_REQUEST = "D2C-E113"
MISSING_PLANNER = "D2C-E120"
PRIVATE_ACCESS = "D2C-E121"
SCHEMA_DRIFT = "D2C-E130"
EQUIPMENT_CATALOG = "D2C-E140"
NO_USABLE_VARIANT = "D2C-E150"

UNKNOWN_SELECTION = "D2C-W101"
UNUSABLE_VARIANT = "D2C-W102"
EQUIPMENT_JOIN = "D2C-W110"
OPTIONAL_ENTRY_JOIN = "D2C-W120"
OPTIONAL_CATALOG = "D2C-W121"
OPTIONAL_NO_OUTPUT = "D2C-W122"


@dataclass
class D2CoreImportError(ImportSourceError):
    """Expected, redacted source failure carrying a stable user-facing code."""

    code: str
    detail: str
    retryable: bool = False
    context: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.detail)

    @override
    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class D2CoreCatalogError(D2CoreImportError):
    """Catalog transport or schema failure."""


class D2CoreBrowserError(D2CoreImportError):
    """Browser acquisition failure."""
