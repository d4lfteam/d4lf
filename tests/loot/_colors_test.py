from src import loot


def test_default_filter_colors_have_all_rendering_roles(monkeypatch):
    monkeypatch.setattr("src.loot._colors.get_settings", lambda: (_ for _ in ()).throw(RuntimeError()))
    colors = loot.get_filter_colors()
    assert colors.matched
    assert colors.no_match
    assert colors.processing
