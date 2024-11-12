import logging
import time
from enum import Enum

import keyboard
import numpy as np

from src.template_finder import SearchArgs, SearchResult
from src.utils.misc import run_until_condition

LOGGER = logging.getLogger(__name__)


class ToggleMethod(Enum):
    BUTTON = 1
    HOTKEY = 2


class Menu:
    def __init__(self):
        self.menu_name: str = ""
        self.parent_menu: Menu | None = None
        self.is_open_search_args: SearchArgs | None = None
        self.open_hotkey: str = ""
        self.delay = 0

    def open(self) -> bool:
        """
        Opens the menu by clicking the open button.
        :return: True if the menu is successfully opened, False otherwise.
        """
        # Open parent menu if there is one to be opened
        if self.parent_menu and not self.is_open() and not self.parent_menu.open():
            LOGGER.error(f"Could not open parent menu {self.parent_menu.menu_name}")
            return False
        if not (is_open := self.is_open()):
            LOGGER.debug(f"Opening {self.menu_name} using hotkey {self.open_hotkey}")
            keyboard.send(self.open_hotkey)
        else:
            LOGGER.debug(f"{self.menu_name} already open")
        return is_open or self.wait_until_open()

    def _check_match(self, res: SearchResult) -> bool:
        """
        Checks if the given TemplateMatch is a match for the menu.
        :param res: The TemplateMatch to check.
        """
        if self.is_open_search_args.mode == "best":
            return res.matches[0].name.lower() == self.is_open_search_args.ref[0].lower()
        return True

    def is_open(self, img: np.ndarray = None) -> bool:
        """
        Checks if the menu is open.
        :return: True if the menu is open, False otherwise.
        """
        res = self.is_open_search_args.detect(img)
        if res.success:
            return self._check_match(res)
        return False

    def wait_until_open(self, timeout: float = 10) -> bool:
        """
        Waits until the menu is open.
        :param timeout: The number of seconds to wait before timing out.
        :return: True if the menu is open, False otherwise.
        """
        _, success = run_until_condition(self.is_open, lambda res: res, timeout)
        if not success:
            LOGGER.warning(f"Could not find {self.menu_name} after {timeout} seconds")
        time.sleep(self.delay)
        return success
