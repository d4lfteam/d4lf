from dataclasses import dataclass

import numpy as np  # ruff:ignore[typing-only-third-party-import] - runtime type-hint introspection resolves np.ndarray


@dataclass
class Template:
    name: str = ""
    img_bgra: np.ndarray | None = None
    img_bgr: np.ndarray | None = None
    img_gray: np.ndarray | None = None
    alpha_mask: np.ndarray | None = None
