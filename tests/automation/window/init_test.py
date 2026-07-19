from src.automation.window import WindowSpec, get_window_spec_id


def test_window_interface_exposes_runtime_operations() -> None:
    assert WindowSpec("Diablo IV.exe").process_name == "Diablo IV.exe"
    assert callable(get_window_spec_id)
