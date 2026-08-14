import annotationlib
import functools
import inspect
import logging
from typing import TYPE_CHECKING, TypeVar, overload

import httpx
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from src.importing.contracts import ImportRequest
from src.settings import BrowserType, get_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from selenium.webdriver.remote.webelement import WebElement

LOGGER = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Diablo 4 Loot Filter - Profile Importer"}
R = TypeVar("R")
type ImporterArgument = ImportRequest | WebDriver | str | bool | None


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


@overload
def retry_importer(func: Callable[..., R], inject_webdriver: bool = False, uc: bool = False) -> Callable[..., R]: ...


@overload
def retry_importer(
    func: None = None, inject_webdriver: bool = False, uc: bool = False
) -> Callable[[Callable[..., R]], Callable[..., R]]: ...


def retry_importer(
    func: Callable[..., R] | None = None, inject_webdriver: bool = False, uc: bool = False
) -> Callable[[Callable[..., R]], Callable[..., R]] | Callable[..., R]:
    def decorator(wrap_function: Callable[..., R]) -> Callable[..., R]:
        signature = inspect.signature(wrap_function, annotation_format=annotationlib.Format.STRING)

        @functools.wraps(wrap_function)
        def wrapper(*args: ImporterArgument, **kwargs: ImporterArgument) -> R:
            bound = signature.bind_partial(*args, **kwargs)
            explicit_driver = bound.arguments.get("driver") is not None
            if not explicit_driver:
                for parameter_name, parameter in signature.parameters.items():
                    if (
                        parameter.kind is inspect.Parameter.VAR_KEYWORD
                        and bound.arguments.get(parameter_name, {}).get("driver") is not None
                    ):
                        explicit_driver = True
                        break
            owns_driver = inject_webdriver and not explicit_driver
            owned_driver = None
            call_args = args
            call_kwargs = kwargs
            if owns_driver:
                owned_driver = setup_webdriver(uc=uc)
                if "driver" in signature.parameters:
                    bound.arguments["driver"] = owned_driver
                    call_args, call_kwargs = bound.args, bound.kwargs
                else:
                    call_kwargs = {**kwargs, "driver": owned_driver}
            try:
                for attempt in range(2):
                    try:
                        return wrap_function(*call_args, **call_kwargs)
                    except Exception:
                        LOGGER.exception("An error occurred while importing. Retrying...")
                        if attempt == 1:
                            raise
            finally:
                if owned_driver is not None:
                    owned_driver.quit()
            msg = "Importer retry loop exited unexpectedly"
            raise RuntimeError(msg)

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
            options.enable_bidi = True
            options.add_argument("--headless=new")
            options.add_argument("log-level=3")
            options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
            return webdriver.Edge(options=options)
        case BrowserType.chrome:
            options = webdriver.ChromeOptions()
            options.enable_bidi = True
            options.add_argument("--headless=new")
            options.add_argument("log-level=3")
            options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
            return webdriver.Chrome(options=options)
        case BrowserType.firefox:
            options = webdriver.FirefoxOptions()
            options.enable_bidi = True
            options.add_argument("--headless")
            options.set_preference("general.useragent.override", HEADERS["User-Agent"])
            return webdriver.Firefox(options=options)
    msg = "Unsupported browser configured for profile importer"
    raise ValueError(msg)
