"""New config loading and verification using pydantic. For now, both will exist in parallel hence _new."""

import configparser
import logging
import pathlib
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QThread, QTimer

from src.config.helper import singleton
from src.config.models import DEPRECATED_INI_KEYS, AdvancedOptionsModel, CharModel, GeneralModel

LOGGER = logging.getLogger(__name__)
PARAMS_INI = "params.ini"


@singleton
class IniConfigLoader:
    def __init__(self):
        self._advanced_options = AdvancedOptionsModel()
        self._char = CharModel()
        self._general = GeneralModel()
        self._parser = None
        self._user_dir = pathlib.Path.home() / ".d4lf"
        self._user_dir.mkdir(parents=True, exist_ok=True)
        self._pending_write = False
        self.load()

    def load(self, clear: bool = False):
        if not (self.user_dir / PARAMS_INI).exists() or clear:
            with Path(self.user_dir / PARAMS_INI).open("w", encoding="utf-8"):
                pass

        self._parser = configparser.ConfigParser()
        self._parser.read(self.user_dir / PARAMS_INI, encoding="utf-8")

        all_keys = [key for section in self._parser.sections() for key in self._parser[section]]
        deprecated_keys = [key for key in DEPRECATED_INI_KEYS if key in all_keys]
        for key in deprecated_keys:
            LOGGER.warning(f"Deprecated {key=} found in {PARAMS_INI}. Please remove this key from your config file.")
            for section in self._parser.sections():
                if key in self._parser[section]:
                    self._parser.remove_option(section, key)

        if "advanced_options" in self._parser:
            self._advanced_options = AdvancedOptionsModel(**self._parser["advanced_options"])
        else:
            self._advanced_options = AdvancedOptionsModel()

        if "char" in self._parser:
            self._char = CharModel(**self._parser["char"])
        else:
            self._char = CharModel()

        if "general" in self._parser:
            self._general = GeneralModel(**self._parser["general"])
        else:
            self._general = GeneralModel()

    @property
    def advanced_options(self) -> AdvancedOptionsModel:
        return self._advanced_options

    @property
    def char(self) -> CharModel:
        return self._char

    @property
    def general(self) -> GeneralModel:
        return self._general

    @property
    def user_dir(self) -> Path:
        return self._user_dir

    def _refresh_models_from_parser(self, section: str) -> None:
        """Best-effort: keep the pydantic models in sync with the underlying parser."""
        if self._parser is None:
            return

        try:
            if section == "advanced_options" and "advanced_options" in self._parser:
                self._advanced_options = AdvancedOptionsModel(**self._parser["advanced_options"])
            elif section == "char" and "char" in self._parser:
                self._char = CharModel(**self._parser["char"])
            elif section == "general" and "general" in self._parser:
                self._general = GeneralModel(**self._parser["general"])
        except Exception:
            LOGGER.exception("Failed to refresh config models after save_value")

    def save_value(self, section: str, key: str, value: str, flush: bool = False) -> None:
        if self._parser is None:
            self.load()

        if not self._parser.has_section(section):
            self._parser.add_section(section)

        self._parser.set(section, key, value)
        self._refresh_models_from_parser(section)

        # In the GUI we coalesce multiple writes into the same event loop tick.
        # In worker threads / CLI contexts, there may be no Qt event loop, so write immediately.
        if flush:
            self._write_to_disk()
            return

        app = QCoreApplication.instance()
        if app is None or QThread.currentThread() != app.thread():
            self._write_to_disk()
            return

        if not self._pending_write:
            self._pending_write = True
            QTimer.singleShot(0, self._write_to_disk)

    def _write_to_disk(self):
        try:
            with Path(self.user_dir / PARAMS_INI).open("w", encoding="utf-8") as config_file:
                self._parser.write(config_file)
        except Exception as e:
            LOGGER.error(f"Failed to write config file: {e}")
        finally:
            self._pending_write = False


if __name__ == "__main__":
    a = IniConfigLoader()
    a.load()
