import pytest

from src.importing.d2core.errors import SCHEMA_DRIFT, D2CoreImportError
from src.importing.d2core.source.helpers import class_name, decode_body, select_variant_name
from src.importing.filters import PLAYER_CLASSES


def test_source_helpers_provide_stable_variant_labels_and_schema_errors() -> None:
    assert select_variant_name({"name": ""}, 3) == "Variant 3"
    with pytest.raises(D2CoreImportError) as error:
        decode_body("not-json")
    assert error.value.code == SCHEMA_DRIFT


def test_unknown_class_metadata_does_not_log_source_text(caplog) -> None:
    caplog.set_level("ERROR")

    assert class_name("private owner description") == "Unknown"
    assert not caplog.records


@pytest.mark.parametrize("source_class", PLAYER_CLASSES)
def test_recognized_classes_keep_catalog_driven_metadata(source_class: str) -> None:
    assert class_name(source_class) == source_class.title()
