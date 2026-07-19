import ast
from pathlib import Path


def test_data_generation_entrypoint_exports_run() -> None:
    tree = ast.parse(Path("src/tools/data_generation/__main__.py").read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.FunctionDef) and node.name == "run" for node in tree.body)
