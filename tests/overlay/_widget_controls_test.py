from src.overlay._widget_controls import _OverlayControls


def test_toggle_orientation_repackages_and_persists():
    overlay = object.__new__(_OverlayControls)
    overlay.orientation = "horizontal"
    overlay.overlay_frame = type("Frame", (), {"config": lambda *_args, **_kwargs: None})()
    overlay._repack = lambda: None
    saved = []
    overlay._save_settings = lambda: saved.append(True)

    overlay._toggle_orientation()

    assert overlay.orientation == "vertical"
    assert saved == [True]
