from src.importing import ImportOptions, ImportRequest, VariantSelection
from src.importing.d2core.source.workflow import resolve_variants


def test_multi_variant_resolution_preserves_source_order_and_warns_unknown_ids() -> None:
    variants = [{"name": "first"}, {"name": "second"}, {"name": "third"}]
    warnings: list[tuple[str, str, str, str]] = []
    request = ImportRequest(
        "https://d2core.com/d4/planner?bd=offline",
        options=ImportOptions(multi_build=True),
        variant_selection=VariantSelection(("3", "1", "3", "9")),
    )

    def warn(code: str, variant: str, module: str, key: str) -> None:
        warnings.append((code, variant, module, key))

    selected = resolve_variants(variants, None, request, warn)

    assert [index for index, _ in selected] == [1, 3]
    assert warnings == [("D2C-W101", "", "selection", "9")]
