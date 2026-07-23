import src.tools


def test_tools_package_is_importable() -> None:
    assert src.tools.__name__ == "src.tools"
