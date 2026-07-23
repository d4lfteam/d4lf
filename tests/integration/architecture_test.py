from pathlib import Path


def _relative_python_files(root: Path, directory: str) -> set[Path]:
    return {path.relative_to(root) for path in (root / directory).rglob("*.py")}


def _expected_unit_test_path(source_path: Path) -> Path:
    relative = source_path.relative_to("src")
    if relative.name == "__init__.py":
        return Path("tests", *relative.parts[:-1], "init_test.py")
    return Path("tests", *relative.parts[:-1], f"{relative.stem}_test.py")


def test_source_modules_have_exactly_one_mirrored_unit_test():
    root = Path(__file__).resolve().parents[2]
    source_files = _relative_python_files(root, "src")
    unit_files = {
        path
        for path in _relative_python_files(root, "tests")
        if "integration" not in path.parts and path.name not in {"conftest.py", "__init__.py"}
    }
    expected_files = {_expected_unit_test_path(path) for path in source_files}

    assert unit_files == expected_files
