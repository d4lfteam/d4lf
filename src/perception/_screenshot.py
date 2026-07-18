import logging
import pathlib
from datetime import datetime

import cv2

from src.logger import LOG_DIR
from src.perception._capture import Cam

LOGGER = logging.getLogger(__name__)


def screenshot(
    name: str | None = None,
    path: str = str(LOG_DIR / "screenshots"),
    img=None,
    overwrite: bool = True,
    timestamp: bool = True,
) -> None:
    name = name if name is not None else "screenshot"
    img = img if img is not None else Cam().grab()
    pathlib.Path(path).mkdir(exist_ok=True, parents=True)
    suffix = "_" + datetime.now(tz=None).strftime("%Y%m%d_%H%M%S.%f") if timestamp else ""  # ruff:ignore[call-datetime-now-without-tzinfo]
    file_path = pathlib.Path(path) / f"{name}{suffix}.png"

    if file_path.exists() and not overwrite:
        LOGGER.warning(f"{name} already exists, not overwriting because overwrite is set to False.")
        return
    if file_path.exists():
        LOGGER.warning(f"{name} already exists, overwriting.")
    cv2.imwrite(str(file_path), img)
    LOGGER.debug(f"Saved screenshot: {file_path}")
