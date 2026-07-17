import functools
import logging
import time
from typing import TYPE_CHECKING, Literal

import httpx
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from src.settings import BrowserType, get_settings

if TYPE_CHECKING:
    from collections.abc import Callable

LOGGER = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Diablo 4 Loot Filter - Profile Importer"}


def get_with_retry(url: str, custom_headers: dict[str, str] | None = None) -> httpx.Response:
    for _ in range(10):
        try:
            response = httpx.get(url, headers=custom_headers if custom_headers is not None else HEADERS)
        except httpx.RequestError:
            LOGGER.debug(f"Request {url} timed out, retrying...")
            continue
        if response.status_code != 200:
            LOGGER.debug(f"Request {url} failed with status code {response.status_code}, retrying...")
            continue
        return response
    LOGGER.error(msg := f"Failed to get a successful response after 10 attempts: {url=}")
    raise ConnectionError(msg)


def handle_popups[T: WebElement](
    driver: WebDriver, method: Callable[[WebDriver], Literal[False] | T], timeout: int = 10
) -> None:
    LOGGER.info("Handling cookie / adblock popups")
    wait = WebDriverWait(driver, timeout)
    for _ in range(3):
        try:
            element = wait.until(method)
        except TimeoutException:
            break
        element.click()
        time.sleep(1)


def hover_and_get_tooltip_html(
    driver: WebDriver, element: WebElement, tooltip_css: str, warn_on_timeout: bool = True
) -> str:
    """Hover an element and return the outerHTML of the tooltip it reveals, if any."""
    driver.execute_script("document.querySelectorAll('[data-tippy-root]').forEach((node) => node.remove());")
    ActionChains(driver).move_to_element(element).perform()
    driver.execute_script(
        "arguments[0].dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));arguments[0].dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));",
        element,
    )
    try:
        tooltip = WebDriverWait(driver, 2).until(ec.presence_of_element_located((By.CSS_SELECTOR, tooltip_css)))
    except TimeoutException:
        if warn_on_timeout:
            LOGGER.warning("Unable to read tooltip for selector %s.", tooltip_css)
        return ""
    return str(tooltip.get_attribute("outerHTML") or "")


def retry_importer(func=None, inject_webdriver: bool = False, uc=False):
    def decorator(wrap_function):
        @functools.wraps(wrap_function)
        def wrapper(*args, **kwargs):
            owns_driver = inject_webdriver and "driver" not in kwargs and not args
            if owns_driver:
                kwargs["driver"] = setup_webdriver(uc=uc)
            try:
                for _ in range(2):
                    try:
                        return wrap_function(*args, **kwargs)
                    except Exception:
                        LOGGER.exception("An error occurred while importing. Retrying...")
                return None
            finally:
                if owns_driver:
                    kwargs["driver"].quit()

        return wrapper

    return decorator if func is None else decorator(func)


def setup_webdriver(uc: bool = False) -> WebDriver:
    if uc:
        driver = Driver(uc=uc, headless2=True, agent=HEADERS["User-Agent"])
        if not isinstance(driver, WebDriver):
            msg = "seleniumbase did not return a Selenium WebDriver"
            raise TypeError(msg)
        return driver
    match get_settings().general.browser:
        case BrowserType.edge:
            options = webdriver.EdgeOptions()
            options.add_argument("--headless=new")
            options.add_argument("log-level=3")
            options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
            return webdriver.Edge(options=options)
        case BrowserType.chrome:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("log-level=3")
            options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
            return webdriver.Chrome(options=options)
        case BrowserType.firefox:
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")
            options.set_preference("general.useragent.override", HEADERS["User-Agent"])
            return webdriver.Firefox(options=options)
    msg = "Unsupported browser configured for profile importer"
    raise ValueError(msg)
