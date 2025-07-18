import json
import logging
import threading

from src.config import BASE_DIR
from src.config.loader import IniConfigLoader
from src.item.data.item_type import ItemType

LOGGER = logging.getLogger(__name__)

DATALOADER_LOCK = threading.Lock()


class Dataloader:
    affix_dict = {}
    affix_sigil_dict = {}
    affix_sigil_dict_all = {}
    aspect_list = []
    aspect_unique_dict = {}
    error_map = {}
    filter_after_keyword = []
    filter_words = []
    item_types_dict = {}
    tooltips = {}
    tribute_dict = {}

    _instance = None
    data_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            with DATALOADER_LOCK:
                if not cls._instance.data_loaded:
                    cls._instance.data_loaded = True
                    cls._instance.load_data()
        return cls._instance

    def load_data(self):
        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/affixes.json", encoding="utf-8") as f:
            self.affix_dict: dict = json.load(f)

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/aspects.json", encoding="utf-8") as f:
            self.aspect_list = json.load(f)

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/corrections.json", encoding="utf-8") as f:
            data = json.load(f)
            self.error_map = data["error_map"]
            self.filter_after_keyword = data["filter_after_keyword"]
            self.filter_words = data["filter_words"]

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/item_types.json", encoding="utf-8") as f:
            data = json.load(f)
            self.item_types_dict = data
            for item, value in data.items():
                if item in ItemType.__members__:
                    enum_member = ItemType[item]
                    enum_member._value_ = value
                else:
                    LOGGER.warning(f"{item} type not in item_type.py")

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/sigils.json", encoding="utf-8") as f:
            self.affix_sigil_dict_all = json.load(f)
            self.affix_sigil_dict = {
                **self.affix_sigil_dict_all["dungeons"],
                **self.affix_sigil_dict_all["minor"],
                **self.affix_sigil_dict_all["major"],
                **self.affix_sigil_dict_all["positive"],
            }

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/tributes.json", encoding="utf-8") as f:
            self.tribute_dict: dict = json.load(f)

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/tooltips.json", encoding="utf-8") as f:
            self.tooltips = json.load(f)

        with open(BASE_DIR / f"assets/lang/{IniConfigLoader().general.language}/uniques.json", encoding="utf-8") as f:
            self.aspect_unique_dict = json.load(f)
