from src.automation._menu import Menu


def test_menu_starts_closed_without_search_configuration():
    menu = Menu()
    assert not menu.menu_name
    assert not menu.open_hotkey
