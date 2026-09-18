import src


def test_root_package_exposes_version_without_matching_executor() -> None:
    assert src.__version__ == "10.0.4"
    assert not hasattr(src, "TP")
