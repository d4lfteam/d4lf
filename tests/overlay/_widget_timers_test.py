import datetime

from src.overlay._widget_timers import _OverlayTimers


def test_fetch_schedule_selects_next_world_boss(monkeypatch):
    now = datetime.datetime.now(datetime.UTC)
    start = (now + datetime.timedelta(hours=1)).isoformat()

    class Response:
        status_code = 200

        def json(self):
            return {"world_boss": [{"startTime": start, "boss": "Ashava"}]}

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, _url):
            return Response()

    overlay = object.__new__(_OverlayTimers)
    overlay._save_settings = lambda: None
    overlay.winfo_exists = lambda: True
    overlay._update_timers = lambda: None
    overlay.after = lambda *_args: None
    monkeypatch.setattr("src.overlay._widget_timers.httpx.Client", lambda **_kwargs: Client())

    overlay._fetch_schedule()

    assert overlay.next_boss_name == "Ashava"
    assert overlay.synced_wb[1] == "Ashava"
