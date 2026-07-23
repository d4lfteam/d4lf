from src.overlay.widget import menu as _widget_menu
from src.overlay.widget.menu import _OverlayMenu


def test_context_menu_records_pointer_position(monkeypatch):
    class FakeWidget:
        def __init__(self, *_args, **_kwargs):
            self.geometry_value = None

        def __getattr__(self, _name):
            return lambda *_args, **_kwargs: self

        def geometry(self, value):
            self.geometry_value = value

    monkeypatch.setattr(_widget_menu.tk, "Toplevel", FakeWidget)
    monkeypatch.setattr(_widget_menu.tk, "Frame", FakeWidget)
    monkeypatch.setattr(_widget_menu.tk, "Label", FakeWidget)
    monkeypatch.setattr(_widget_menu.tk, "Button", FakeWidget)

    overlay = object.__new__(_OverlayMenu)
    overlay.font_family = "Consolas"
    overlay.font_size = 14
    overlay.orientation = "horizontal"
    overlay.locked = False
    overlay.settings = {"exp_bar_pos": None, "exp_age_before_refresh": 5}
    overlay.FONT_CHOICES = ("Consolas",)
    overlay.show_wb = overlay.show_legion = overlay.show_ht = True
    overlay.capture_gold_stats = overlay.capture_exp_stats = False
    overlay.show_gph = overlay.show_total_gold = True
    overlay.show_eph = overlay.show_total_exp = overlay.show_t2l = overlay.show_next_scan = True
    overlay._last_menu_pos = (100, 100)
    overlay._create_toggle_btn = lambda *_args, **_kwargs: FakeWidget()
    overlay._create_config_toggle_btn = lambda *_args, **_kwargs: FakeWidget()
    overlay._create_radio_button = lambda *_args, **_kwargs: FakeWidget()
    overlay._create_submenu_button = lambda *_args, **_kwargs: FakeWidget()
    overlay._destroy_settings_popup = lambda: None
    overlay._on_popup_focus_out = lambda _event: None
    overlay._close_all_submenus = lambda: None
    overlay._auto_sync = lambda: None
    overlay._toggle_lock = lambda: None
    overlay._change_size = lambda _delta: None
    overlay._toggle_orientation = lambda: None
    overlay._show_context_menu = _OverlayMenu._show_context_menu.__get__(overlay)

    event = type("Event", (), {"x_root": 320, "y_root": 240})()
    overlay._show_context_menu(event)

    assert overlay._last_menu_pos == (320, 240)
    assert overlay._settings_popup.geometry_value == "+320+240"
