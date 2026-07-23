from src.tools.data_generation import main


def test_data_generation_facade_exports_main() -> None:
    assert callable(main)
