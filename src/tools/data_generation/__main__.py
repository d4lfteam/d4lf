"""Command-line entry point for data generation."""

import argparse
from pathlib import Path

from src.tools.data_generation.common import D4LF_BASE_DIR
from src.tools.data_generation.datasets import main


def run() -> int:
    parser = argparse.ArgumentParser(description="Generate D4LF data from a d4data checkout")
    parser.add_argument("d4data_dir", nargs="?", type=Path, default=D4LF_BASE_DIR.parent / "d4data")
    path = parser.parse_args().d4data_dir
    if not path.exists() or not path.is_dir():
        print(f"The provided path '{path}' does not exist or is not a directory.")
        return 0
    main(path)
    return 0


raise SystemExit(run())
