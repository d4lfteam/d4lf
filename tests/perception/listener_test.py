import logging

from src.perception.listener import Publisher, filter_data, find_item_start, fix_data


def test_listener_identifies_item_start_and_cleans_tts_markers() -> None:
    assert find_item_start(["Noise", "RARE SWORD", "Right mouse button"]) == 1
    assert filter_data("Champions who earn the favor of the season")
    assert fix_data("[MARKED AS JUNK]. [FAVORITED ITEM]. Name") == "Name"


def test_listener_item_publication_logs_raw_tts_payload(caplog) -> None:
    payload = ["RARE SWORD", "Right mouse button"]

    with caplog.at_level(logging.DEBUG, logger="src.perception.listener"):
        Publisher().publish_item(payload)

    assert f"Raw TTS payload: {payload}" in caplog.messages
