from src.importing.gui.variant_dialog import select_variants_dialog


def test_select_variants_dialog_is_callable() -> None:
    assert callable(select_variants_dialog)
