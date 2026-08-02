from src.importing.d2core import source
from src.importing.d2core.source.core import D2CoreImportSource, PlannerSnapshot


def test_source_facade_exports_the_planner_source_contract() -> None:
    assert source.__all__ == ["D2CoreImportSource", "PlannerSnapshot"]
    assert source.D2CoreImportSource is D2CoreImportSource
    assert source.PlannerSnapshot is PlannerSnapshot
