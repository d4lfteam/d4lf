import json

from src.importing.d2core.browser.capture import body_matches_build, is_catalog_url


def test_capture_helpers_require_versioned_english_catalog_and_build() -> None:
    body = json.dumps({"data": {"response_data": json.dumps({"data": {"_id": "offline"}})}})

    assert is_catalog_url("https://cloudstorage.d2core.com/data/d4/v1/affix_enUS.json?env=prod&v=8")
    assert not is_catalog_url("https://cloudstorage.d2core.com/data/d4/affix_enUS.json")
    assert body_matches_build(body, "offline")
    assert not body_matches_build(body, "other")
