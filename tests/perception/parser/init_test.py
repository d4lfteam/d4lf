from src.perception.parser import parse_item_text


def test_parser_interface_exposes_item_parser() -> None:
    assert callable(parse_item_text)
