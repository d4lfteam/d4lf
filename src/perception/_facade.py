from . import _listener
from ._parser_item import parse_item_text

Publisher = _listener.Publisher
filter_data = _listener.filter_data
find_item_start = _listener.find_item_start
fix_data = _listener.fix_data


def read_latest_item():
    return parse_item_text(list(_listener.LAST_ITEM))


def latest_item_lines() -> list[str]:
    return list(_listener.LAST_ITEM)


def is_connected() -> bool:
    return _listener.CONNECTED


def start_connection() -> None:
    _listener.start_connection()
