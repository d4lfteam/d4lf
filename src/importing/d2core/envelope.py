"""Validation of the nested CloudBase planner response."""

import json
from collections.abc import Mapping
from typing import cast

from src.importing.d2core.errors import (
    INTERACTIVE_ACCESS,
    MISSING_PLANNER,
    PRIVATE_ACCESS,
    SCHEMA_DRIFT,
    SIGNED_REQUEST,
    D2CoreImportError,
)
from src.type_aliases import JsonObject, JsonValue

_TERMINAL_CODES = {
    "captcha_required": INTERACTIVE_ACCESS,
    "invalid_app_sign": SIGNED_REQUEST,
    "private_build": PRIVATE_ACCESS,
    "build_not_found": MISSING_PLANNER,
}
_TERMINAL_DETAILS = {
    INTERACTIVE_ACCESS: "d2core requires interactive access",
    SIGNED_REQUEST: "The signed d2core planner request failed",
    PRIVATE_ACCESS: "The d2core planner is private or access denied",
    MISSING_PLANNER: "The d2core planner was not found or was deleted",
}

type _EnvelopeLevel = JsonObject | None
type _Envelope = tuple[JsonObject, _EnvelopeLevel, _EnvelopeLevel, str | None, Exception | None]


def decode_build_envelope(body: str | Mapping[str, JsonValue], build_id: str) -> JsonObject:
    """Decode and validate the redacted shape needed by the importer."""
    outer, response, build, terminal, response_error = _parse_envelope(body)
    if not outer:
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response envelope was not an object")
    if response is outer and build is outer:
        return validate_build(outer, build_id)

    if terminal is not None:
        raise D2CoreImportError(terminal, _TERMINAL_DETAILS[terminal])
    if response is None:
        if response_error is not None:
            raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response data was not valid JSON") from response_error
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response data was missing")
    if not build:
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core build payload was missing")
    return validate_build(build, build_id)


def validate_build(value: JsonValue, build_id: str) -> JsonObject:
    """Validate a decoded planner build, including offline source snapshots."""
    build = _mapping(value)
    if not build:
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core build payload was missing")
    if str(build.get("_id", build.get("id", ""))) != build_id:
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core response did not match the requested build")
    if not isinstance(build.get("is_public"), bool) or not isinstance(build.get("deleted"), bool):
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core build public/deleted state was malformed")
    if build.get("deleted") is True:
        raise D2CoreImportError(MISSING_PLANNER, "The d2core planner was deleted")
    if build.get("is_public") is False:
        raise D2CoreImportError(PRIVATE_ACCESS, "The d2core planner is private")
    variants = build.get("variants")
    if not isinstance(variants, list) or any(not _valid_variant(variant) for variant in variants):
        raise D2CoreImportError(SCHEMA_DRIFT, "The d2core build did not contain a Variant list")
    return dict(build)


def _mapping(value: JsonValue) -> JsonObject:
    if not isinstance(value, Mapping):
        return {}
    source = cast("Mapping[str, JsonValue]", value)
    return {str(key): item for key, item in source.items()}


def _valid_variant(value: JsonValue) -> bool:
    if not isinstance(value, Mapping):
        return False
    source = cast("Mapping[str, JsonValue]", value)
    return all(
        field not in source or isinstance(source[field], expected)
        for field, expected in (("gear", Mapping), ("charms", list), ("paragon", Mapping))
    )


def _terminal_code(value: JsonValue) -> str | None:
    """Classify one CloudBase response object without traversing arbitrary payloads."""
    parsed = _mapping(value)
    if not parsed:
        return None
    raw_code = parsed.get("code", parsed.get("error_code", parsed.get("errorCode")))
    normalized_code = str(raw_code or "").casefold().replace("-", "_")
    if normalized_code in _TERMINAL_CODES:
        return _TERMINAL_CODES[normalized_code]
    if parsed.get("deleted") is True:
        return MISSING_PLANNER
    if parsed.get("is_public") is False:
        return PRIVATE_ACCESS
    return None


def terminal_envelope_code(value: JsonValue) -> str | None:
    """Return a terminal planner error in the CloudBase response wrapper."""
    return _parse_envelope(value)[3]


def _parse_envelope(value: JsonValue) -> _Envelope:
    """Parse and classify only the observed outer/data/response_data/build levels."""
    parsed: JsonValue = value
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            return {}, None, None, None, None
    outer = _mapping(parsed)
    if not outer:
        return {}, None, None, None, None

    if "_id" in outer and "data" not in outer:
        return outer, outer, outer, _terminal_code(outer), None

    data = _mapping(outer.get("data"))
    if not data:
        return outer, None, None, _terminal_code(outer), None

    raw_response = data.get("response_data")
    if isinstance(raw_response, str):
        try:
            raw_response = json.loads(raw_response)
        except json.JSONDecodeError as error:
            return outer, None, None, _terminal_code(outer) or _terminal_code(data), error
    response = _mapping(raw_response) or data
    build = _mapping(response.get("data"))
    terminal = next((code for level in (outer, data, response, build) if (code := _terminal_code(level))), None)
    return outer, response, build, terminal, None
