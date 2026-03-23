from pathlib import Path
from types import SimpleNamespace

from src.app_runtime import AppRuntime


class FakeConfig:
    def __init__(self):
        self.user_dir = Path("C:/fake/.d4lf")
        self.advanced_options = SimpleNamespace(process_name="Diablo IV.exe")


class FakeFilter:
    def __init__(self, events):
        self.events = events

    def load_files(self):
        self.events.append("load_files")


class FakeCam:
    def __init__(self, events, states=None):
        self.events = events
        self.states = list(states or [True])

    def is_offset_set(self):
        self.events.append("is_offset_set")
        return self.states.pop(0)


class FakeTTS:
    def __init__(self, events):
        self.events = events

    def start_connection(self):
        self.events.append("start_tts")


def test_app_runtime_runs_shared_boot_sequence_in_order():
    events = []

    class FakeOverlay:
        def run(self):
            events.append("overlay_run")

    runtime = AppRuntime(
        config_loader=FakeConfig(),
        filter_loader=FakeFilter(events),
        cam=FakeCam(events),
        tts_module=FakeTTS(events),
        overlay_factory=FakeOverlay,
        script_handler_factory=lambda: events.append("create_script_handler"),
        window_detector=lambda spec: events.append(("start_detecting_window", spec)),
        window_spec_factory=lambda process_name: f"spec:{process_name}",
        update_notifier=lambda: events.append("notify_if_update"),
        tts_validator=lambda: events.append("validate_tts"),
        ensure_dirs=lambda *paths: events.append(("ensure_dirs", paths)),
        log_dir=Path("C:/fake/logs"),
        sleep=lambda seconds: events.append(("sleep", seconds)),
    )

    runtime.start_runtime(running_from_source=False)

    assert events == [
        ("ensure_dirs", (Path("C:/fake/logs/screenshots"), Path("C:/fake/.d4lf"), Path("C:/fake/.d4lf/profiles"))),
        "load_files",
        "notify_if_update",
        ("start_detecting_window", "spec:Diablo IV.exe"),
        "is_offset_set",
        ("sleep", 0.5),
        "create_script_handler",
        "validate_tts",
        "start_tts",
        "overlay_run",
    ]


def test_app_runtime_skips_update_notification_when_running_from_source():
    events = []

    class FakeOverlay:
        def run(self):
            events.append("overlay_run")

    runtime = AppRuntime(
        config_loader=FakeConfig(),
        filter_loader=FakeFilter(events),
        cam=FakeCam(events),
        tts_module=FakeTTS(events),
        overlay_factory=FakeOverlay,
        script_handler_factory=lambda: events.append("create_script_handler"),
        window_detector=lambda spec: events.append(("start_detecting_window", spec)),
        window_spec_factory=lambda process_name: f"spec:{process_name}",
        update_notifier=lambda: events.append("notify_if_update"),
        tts_validator=lambda: events.append("validate_tts"),
        ensure_dirs=lambda *paths: events.append(("ensure_dirs", paths)),
        log_dir=Path("C:/fake/logs"),
        sleep=lambda seconds: events.append(("sleep", seconds)),
    )

    runtime.start_runtime(running_from_source=True)

    assert "notify_if_update" not in events
