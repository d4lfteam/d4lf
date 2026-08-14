import datetime
from typing import TYPE_CHECKING

from src.overlay.widget.widget import BossTimerOverlay

if TYPE_CHECKING:
    from src.type_aliases import JsonValue


def test_fetch_schedule_selects_next_world_boss(monkeypatch) -> None:
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

    def save_settings(_overlay: BossTimerOverlay) -> None:
        pass

    def winfo_exists(_overlay: BossTimerOverlay) -> bool:
        return True

    def update_timers(_overlay: BossTimerOverlay) -> None:
        pass

    def after(_overlay: BossTimerOverlay, *_args: JsonValue, **_kwargs: JsonValue) -> str:
        return "after-id"

    monkeypatch.setattr(BossTimerOverlay, "_save_settings", save_settings)
    monkeypatch.setattr(BossTimerOverlay, "winfo_exists", winfo_exists)
    monkeypatch.setattr(BossTimerOverlay, "_update_timers", update_timers)
    monkeypatch.setattr(BossTimerOverlay, "after", after)
    monkeypatch.setattr("src.overlay.widget.timers.httpx.Client", lambda **_kwargs: Client())

    overlay = object.__new__(BossTimerOverlay)
    overlay._fetch_schedule()

    assert overlay.next_boss_name == "Ashava"
    assert overlay.synced_wb is not None
    assert overlay.synced_wb[1] == "Ashava"
