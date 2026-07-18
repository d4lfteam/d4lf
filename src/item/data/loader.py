import json
import logging
import pathlib
import threading
from typing import TypeGuard

from src.item.data.item_type import ItemType
from src.settings import BASE_DIR, get_settings

LOGGER = logging.getLogger(__name__)

DATALOADER_LOCK = threading.Lock()


def _is_string_map(value: object) -> TypeGuard[dict[str, str]]:
    return isinstance(value, dict) and all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    )


def _load_string_map(path: pathlib.Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as f:
        data: object = json.load(f)
    if not _is_string_map(data):
        msg = f"Expected a JSON object containing only string keys and values: {path}"
        raise ValueError(msg)
    return data


class Dataloader:
    affix_dict: dict[str, str] = {}
    charm_affix_dict: dict[str, str] = {}
    seal_affix_dict: dict[str, str] = {}
    affix_sigil_dict = {}
    affix_sigil_dict_all = {}
    aspect_list = []
    aspect_unique_dict = {}
    bad_tts_uniques = {}
    filter_after_keyword = []
    filter_words = []
    item_types_dict = {}
    set_list = []
    tooltips = {}
    tribute_dict: dict[str, str] = {}

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
        language_dir = pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}")
        self.affix_dict = _load_string_map(language_dir / "affixes.json")
        self.seal_affix_dict = _load_string_map(language_dir / "seals_affixes.json")
        self.charm_affix_dict = _load_string_map(language_dir / "charms_affixes.json")

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/aspects.json").open(
            encoding="utf-8"
        ) as f:
            self.aspect_list = json.load(f)

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/corrections.json").open(
            encoding="utf-8"
        ) as f:
            data = json.load(f)
            self.filter_after_keyword = data["filter_after_keyword"]
            self.filter_words = data["filter_words"]
            self.bad_tts_uniques = data["bad_tts_uniques"]

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/item_types.json").open(
            encoding="utf-8"
        ) as f:
            data = json.load(f)
            self.item_types_dict = data
            for item, value in data.items():
                if item in ItemType.__members__:
                    enum_member = ItemType[item]
                    enum_member._value_ = value
                else:
                    LOGGER.warning(f"{item} type not in item_type.py")

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/sigils.json").open(
            encoding="utf-8"
        ) as f:
            self.affix_sigil_dict_all = json.load(f)
            self.affix_sigil_dict = {
                **self.affix_sigil_dict_all["dungeons"],
                **self.affix_sigil_dict_all["minor"],
                **self.affix_sigil_dict_all["major"],
                **self.affix_sigil_dict_all["positive"],
            }

        self.tribute_dict = _load_string_map(language_dir / "tributes.json")

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/tooltips.json").open(
            encoding="utf-8"
        ) as f:
            self.tooltips = json.load(f)

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/uniques.json").open(
            encoding="utf-8"
        ) as f:
            self.aspect_unique_dict = json.load(f)

        with pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}/sets.json").open(
            encoding="utf-8"
        ) as f:
            self.set_list = json.load(f)
