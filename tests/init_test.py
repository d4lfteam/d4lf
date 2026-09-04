import src


def test_root_package_exposes_version_without_matching_executor() -> None:
    assert src.__version__
    assert not hasattr(src, "TP")
