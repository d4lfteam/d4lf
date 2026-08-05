import json

import pytest

from src.importing.d2core.envelope import decode_build_envelope, terminal_envelope_code
from src.importing.d2core.errors import (
    INTERACTIVE_ACCESS,
    MISSING_PLANNER,
    PRIVATE_ACCESS,
    SCHEMA_DRIFT,
    SIGNED_REQUEST,
    D2CoreImportError,
)


def _body(**build_overrides: object) -> dict[str, object]:
    build = {"_id": "offline", "is_public": True, "deleted": False, "variants": []}
    build.update(build_overrides)
    return {"data": {"response_data": json.dumps({"data": build})}}


def test_decode_build_envelope_validates_requested_identity_and_variants() -> None:
    build = decode_build_envelope(_body(variants=[{"name": "Default"}]), "offline")

    assert build["_id"] == "offline"
    assert build["variants"] == [{"name": "Default"}]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"code": "INVALID_APP_SIGN"}, SIGNED_REQUEST),
        ({"code": "PRIVATE_BUILD"}, PRIVATE_ACCESS),
        ({"code": "CAPTCHA_REQUIRED"}, INTERACTIVE_ACCESS),
        ({"code": "BUILD_NOT_FOUND"}, MISSING_PLANNER),
        ({"data": {"response_data": "not-json"}}, SCHEMA_DRIFT),
    ],
)
def test_decode_build_envelope_classifies_expected_failures(body: dict[str, object], code: str) -> None:
    with pytest.raises(D2CoreImportError) as error:
        decode_build_envelope(body, "offline")

    assert error.value.code == code


def test_decode_build_envelope_classifies_cloudbase_response_data_failure() -> None:
    body = {"data": {"response_data": json.dumps({"code": "PRIVATE_BUILD"})}}

    with pytest.raises(D2CoreImportError) as error:
        decode_build_envelope(body, "offline")

    assert error.value.code == PRIVATE_ACCESS


def test_decode_build_envelope_rejects_non_object_variants() -> None:
    with pytest.raises(D2CoreImportError) as error:
        decode_build_envelope(_body(variants=[None]), "offline")

    assert error.value.code == SCHEMA_DRIFT


def test_decode_build_envelope_requires_public_deleted_state() -> None:
    build = {"_id": "offline", "deleted": False, "variants": []}
    body = {"data": {"response_data": json.dumps({"data": build})}}

    with pytest.raises(D2CoreImportError) as error:
        decode_build_envelope(body, "offline")

    assert error.value.code == SCHEMA_DRIFT


def test_terminal_envelope_code_reads_only_the_cloudbase_response_data() -> None:
    body = {"data": {"response_data": json.dumps({"code": "PRIVATE_BUILD"})}}

    assert terminal_envelope_code(body) == PRIVATE_ACCESS


def test_terminal_envelope_code_reads_build_state_in_response_data() -> None:
    body = {"data": {"response_data": json.dumps({"data": {"deleted": True}})}}

    assert terminal_envelope_code(body) == MISSING_PLANNER


def test_envelope_classification_is_bounded_to_known_wrapper_levels() -> None:
    body = {"data": {"code": "PRIVATE_BUILD", "response_data": json.dumps({"data": {}})}}

    assert terminal_envelope_code(body) == PRIVATE_ACCESS
    with pytest.raises(D2CoreImportError) as error:
        decode_build_envelope(body, "offline")
    assert error.value.code == PRIVATE_ACCESS
