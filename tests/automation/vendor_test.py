from src.automation.vendor import Vendor


def test_vendor_has_vendor_menu_name(monkeypatch):
    coordinates = type(
        "C", (), {"roi": type("R", (), {"slots_8x1": (0, 0, 100, 100), "rel_fav_flag": (0, 0, 1, 1)})()}
    )()
    monkeypatch.setattr("src.automation.inventory.get_ui_coordinates", lambda: coordinates)
    monkeypatch.setattr("src.automation.vendor.create_template_query", lambda **kwargs: kwargs)
    vendor = Vendor()
    assert vendor.menu_name == "Vendor"
