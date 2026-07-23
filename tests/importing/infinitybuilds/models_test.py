from src.importing.infinitybuilds import models as _models


def test_infinitybuilds_models_keep_resolved_gear_type() -> None:
    assert _models._ResolvedGearData
