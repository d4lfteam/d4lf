from src.perception.tooltip import DescrDetection, find_descr


def test_tooltip_interface_exposes_detection() -> None:
    assert DescrDetection is not None
    assert callable(find_descr)
