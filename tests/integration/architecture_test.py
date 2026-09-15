from pathlib import Path

_SOURCE_MODULES_WITHOUT_MIRRORED_TESTS = {
    Path("src/importing/d4builds/constants.py"),
    Path("src/importing/gui/constants.py"),
    Path("src/importing/maxroll/constants.py"),
    Path("src/overlay/widget/shared.py"),
    Path("src/paragon/overlay/theme.py"),
    Path("src/profiles/affix/group/controls.py"),
    Path("src/profiles/affix/group/pools.py"),
    Path("src/profiles/charm_seal/general.py"),
    Path("src/profiles/charm_seal/pools.py"),
    Path("src/settings/constants.py"),
    Path("src/tools/data_generation/constants.py"),
}


def _relative_python_files(root: Path, directory: str) -> set[Path]:
    return {path.relative_to(root) for path in (root / directory).rglob("*.py")}


def _expected_unit_test_path(source_path: Path) -> Path:
    relative = source_path.relative_to("src")
    if relative.name == "__init__.py":
        return Path("tests", *relative.parts[:-1], "init_test.py")
    return Path("tests", *relative.parts[:-1], f"{relative.stem}_test.py")


def test_source_modules_have_exactly_one_mirrored_unit_test() -> None:
    root = Path(__file__).resolve().parents[2]
    source_files = _relative_python_files(root, "src")
    unit_files = {
        path
        for path in _relative_python_files(root, "tests")
        if "integration" not in path.parts and path.name not in {"conftest.py", "__init__.py"}
    }
    expected_files = {
        _expected_unit_test_path(path) for path in source_files if path not in _SOURCE_MODULES_WITHOUT_MIRRORED_TESTS
    }

    assert unit_files == expected_files
