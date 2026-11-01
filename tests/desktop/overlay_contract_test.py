import tkinter as tk

import pytest

from src.desktop.overlay_contract import OverlayContract


def test_overlay_contract_is_a_toplevel_that_rejects_unknown_attributes() -> None:
    assert issubclass(OverlayContract, tk.Toplevel)
    with pytest.raises(AttributeError, match="missing"):
        OverlayContract.__getattr__(object.__new__(OverlayContract), "missing")
