import src


def test_root_package_exposes_version_and_executor() -> None:
    assert src.__version__
    assert src.TP is not None
