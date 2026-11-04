"""Public browser acquisition contracts for d2core."""

from src.importing.d2core.browser.bidi import BrowserSnapshot, SeleniumNetworkObserver
from src.importing.d2core.browser.core import BrowserAcquirer, BrowserFactory, NetworkObserver, SeleniumBrowserFactory

__all__ = [
    "BrowserAcquirer",
    "BrowserFactory",
    "BrowserSnapshot",
    "NetworkObserver",
    "SeleniumBrowserFactory",
    "SeleniumNetworkObserver",
]
