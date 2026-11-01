"""Base class for overlay mixins that share a single Tk window."""

import tkinter as tk
from typing import NoReturn


class OverlayContract(tk.Toplevel):
    """Shared Tk base whose subclasses declare the attributes their mixins rely on."""

    def __getattr__(self, name: str) -> NoReturn:
        raise AttributeError(name)
