"""Settings paths and persistent-file names."""

import sys
from pathlib import Path

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent.parent
PARAMS_INI = "params.ini"

__all__ = ["BASE_DIR", "PARAMS_INI"]
