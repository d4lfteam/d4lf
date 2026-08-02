"""Session-local diagnostics for d2core's recoverable import degradation."""

import logging
from dataclasses import dataclass, field

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WarningKey:
    """Stable identity used to deduplicate one recoverable warning."""

    code: str
    variant: str
    module: str
    key: str


@dataclass(slots=True)
class D2CoreWarningSink:
    """Collect and log one warning per code/Variant/module/stable-key tuple."""

    logger: logging.Logger = field(default=LOGGER)
    _seen: set[WarningKey] = field(default_factory=set)
    _current_variant: str = ""
    count: int = 0

    def set_variant(self, variant: str) -> None:
        self._current_variant = variant

    def warn(self, code: str, variant: str, module: str, key: str) -> None:
        effective_variant = self._current_variant or variant
        marker = WarningKey(code, effective_variant, module, key)
        if marker in self._seen:
            return
        self._seen.add(marker)
        self.count += 1
        context = " ".join(value for value in (variant, module, key) if value)
        self.logger.warning("%s d2core import degraded%s", code, f" ({context})" if context else "")

    def clear(self) -> None:
        self._seen.clear()
        self._current_variant = ""
        self.count = 0
