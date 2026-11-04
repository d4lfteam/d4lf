from src.importing.d2core import browser
from src.importing.d2core.browser.bidi import BrowserSnapshot, SeleniumNetworkObserver
from src.importing.d2core.browser.core import BrowserAcquirer, BrowserFactory, NetworkObserver, SeleniumBrowserFactory


def test_browser_facade_exports_the_acquisition_contracts() -> None:
    expected = [
        "BrowserAcquirer",
        "BrowserFactory",
        "BrowserSnapshot",
        "NetworkObserver",
        "SeleniumBrowserFactory",
        "SeleniumNetworkObserver",
    ]

    assert browser.__all__ == expected
    assert [getattr(browser, name) for name in expected] == [
        BrowserAcquirer,
        BrowserFactory,
        BrowserSnapshot,
        NetworkObserver,
        SeleniumBrowserFactory,
        SeleniumNetworkObserver,
    ]
