import datetime
import functools
import logging
import re
import shutil
import time
from typing import TYPE_CHECKING, Literal, TypeVar

import httpx
from ruamel.yaml import YAML, StringIO
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import SB

from src import __version__
from src.config.loader import IniConfigLoader
from src.config.models import BrowserType, ProfileModel
from src.item.data.item_type import ItemType

if TYPE_CHECKING:
    from collections.abc import Callable

    from selenium.webdriver.chromium.webdriver import ChromiumDriver

LOGGER = logging.getLogger(__name__)

D = TypeVar("D", bound=WebDriver | WebElement)
T = TypeVar("T")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}


def extract_digits(text: str) -> int:
    return int("".join([char for char in text if char.isdigit()]))


def fix_weapon_type(input_str: str) -> ItemType | None:
    input_str = input_str.lower()
    if "1h axe" in input_str:
        return ItemType.Axe
    if "1h mace" in input_str:
        return ItemType.Mace
    if "1h sword" in input_str:
        return ItemType.Sword
    if "2h axe" in input_str:
        return ItemType.Axe2H
    if "2h mace" in input_str:
        return ItemType.Mace2H
    if "2h scythe" in input_str:
        return ItemType.Scythe2H
    if "2h sword" in input_str:
        return ItemType.Sword2H
    if "bow" in input_str:
        return ItemType.Bow
    if "crossbow" in input_str:
        return ItemType.Crossbow2H
    if "dagger" in input_str:
        return ItemType.Dagger
    if "flail" in input_str:
        return ItemType.Flail
    if "glaive" in input_str:
        return ItemType.Glaive
    if "polearm" in input_str:
        return ItemType.Polearm
    if "quarterstaff" in input_str:
        return ItemType.Quarterstaff
    if "scythe" in input_str:
        return ItemType.Scythe
    if "staff" in input_str:
        return ItemType.Staff
    if "wand" in input_str:
        return ItemType.Wand
    return None


def fix_offhand_type(input_str: str, class_str: str) -> ItemType | None:
    input_str = input_str.lower()
    class_str = class_str.lower()
    if "sorc" in class_str:
        return ItemType.Focus
    if "druid" in class_str:
        return ItemType.OffHandTotem
    if "necro" in class_str:
        if "focus" in input_str or ("offhand" in input_str and "lucky hit chance" in input_str):
            return ItemType.Focus
        if "shield" in input_str:
            return ItemType.Shield
    return None


def format_number_as_short_string(n: int) -> str:
    result = n / 1_000_000
    return f"{int(result)}M" if result.is_integer() else f"{result:.2f}M"


def get_class_name(input_str: str) -> str:
    input_str = input_str.lower()
    if "barbarian" in input_str:
        return "Barbarian"
    if "druid" in input_str:
        return "Druid"
    if "necromancer" in input_str:
        return "Necromancer"
    if "rogue" in input_str:
        return "Rogue"
    if "sorcerer" in input_str:
        return "Sorcerer"
    if "spiritborn" in input_str:
        return "Spiritborn"
    if "paladin" in input_str:
        return "Paladin"
    LOGGER.error(f"Couldn't match class name {input_str=}")
    return "Unknown"


def get_with_retry(url: str, custom_headers: dict[str, str] | None = None) -> httpx.Response:
    for _ in range(10):
        try:
            r = httpx.get(url, headers=custom_headers if custom_headers is not None else HEADERS)
        except httpx.RequestError:
            LOGGER.debug(f"Request {url} timed out, retrying...")
            continue
        if r.status_code != 200:
            LOGGER.debug(f"Request {url} failed with status code {r.status_code}, retrying...")
            continue
        return r
    LOGGER.error(msg := f"Failed to get a successful response after 10 attempts: {url=}")
    raise ConnectionError(msg)


def handle_popups[D: WebDriver | WebElement, T](driver: ChromiumDriver, method: Callable[[D], Literal[False] | T], timeout: int = 10):
    LOGGER.info("Handling cookie / adblock popups")
    wait = WebDriverWait(driver, timeout)
    for _ in range(3):
        try:
            elem = wait.until(method)
        except TimeoutException:
            break
        elem.click()
        time.sleep(1)


def match_to_enum(enum_class, target_string: str, check_keys: bool = False):
    target_string = target_string.casefold().replace(" ", "").replace("-", "")
    for enum_member in enum_class:
        if enum_member.value.casefold().replace(" ", "").replace("-", "") == target_string:
            return enum_member
        if check_keys and enum_member.name.casefold().replace(" ", "").replace("-", "") == target_string:
            return enum_member
    return None


def retry_importer(func=None, inject_webdriver: bool = False, uc=False):
    def decorator_retry_importer(wrap_function):
        @functools.wraps(wrap_function)
        def wrapper(*args, **kwargs):
            if inject_webdriver and "driver" not in kwargs and not args:
                kwargs["driver"] = setup_webdriver(uc=uc)
            for _ in range(5):
                try:
                    res = wrap_function(*args, **kwargs)
                    if inject_webdriver:
                        kwargs["driver"].quit()
                    return res
                except Exception:
                    LOGGER.exception("An error occurred while importing. Retrying...")
            return None

        return wrapper

    return decorator_retry_importer if func is None else decorator_retry_importer(func)


def save_as_profile(file_name: str, profile: ProfileModel, url: str, exclude=None, backup_file=False) -> str:
    file_name = file_name.replace("'", "")
    file_name = re.sub(r"\W", "_", file_name)
    file_name = re.sub(r"_+", "_", file_name).rstrip("_")
    save_path = IniConfigLoader().user_dir / f"profiles/{file_name}.yaml"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if save_path.exists() and backup_file:
        backup_path = IniConfigLoader().user_dir / f"profiles/backups/{file_name}_original.yaml"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        if not backup_path.exists():  # If already backed up don't overwrite
            shutil.copyfile(save_path, backup_path)

    exclude = exclude if exclude else {"name", "Sigils"}
    with open(save_path, "w", encoding="utf-8") as file:
        file.write(f"# {url}\n")
        file.write(f"# {datetime.datetime.now(tz=datetime.UTC).strftime('%Y-%m-%d %H:%M:%S')} (v{__version__})\n")
        file.write(
            _to_yaml_str(
                profile,
                exclude_defaults=not IniConfigLoader().general.full_dump,
                exclude=exclude,
            )
        )
    LOGGER.info(f"Created profile {save_path}")
    return file_name


def add_to_profiles(build_name):
    profiles = IniConfigLoader().general.profiles
    if build_name in profiles:
        LOGGER.info(f"Profile {build_name} was already an active profile.")
    else:
        profiles.append(build_name)
        IniConfigLoader().save_value("general", "profiles", ", ".join(profiles))
        LOGGER.info(f"Added {build_name} to active profiles configuration")


# Built in to_yaml_str does not preserve the order of the attributes of the model, which is important for uniques
def _to_yaml_str(profile: ProfileModel, exclude_defaults: bool, exclude: set[str]) -> str:
    str_val = profile.model_dump_json(exclude_defaults=exclude_defaults, exclude=exclude)
    yaml = YAML()
    yaml.default_flow_style = None
    dict_val = yaml.load(str_val)
    _rm_style_info(dict_val)
    stream = StringIO()
    yaml.dump(dict_val, stream)
    stream.seek(0)
    return stream.read()


def _rm_style_info(d):
    if isinstance(d, dict):
        d.fa._flow_style = None
        for k, v in d.items():
            _rm_style_info(k)
            _rm_style_info(v)
    elif isinstance(d, list):
        d.fa._flow_style = None
        for elem in d:
            _rm_style_info(elem)


def setup_webdriver(uc: bool = False) -> ChromiumDriver:
    if uc:
        return SB(uc=uc, headless2=True)
    match IniConfigLoader().general.browser:
        case BrowserType.edge:
            options = webdriver.EdgeOptions()
            options.add_argument("--headless=new")
            options.add_argument("log-level=3")
            driver = webdriver.Edge(options=options)
        case BrowserType.chrome:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("log-level=3")
            driver = webdriver.Chrome(options=options)
        case BrowserType.firefox:
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")
            options.add_argument("log-level=3")
            driver = webdriver.Firefox(options=options)
    return driver  # noqa # It must be one of the 3 browsers due to ini validation
