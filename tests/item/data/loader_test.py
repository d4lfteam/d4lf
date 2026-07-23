import json
import threading

import pytest

from src.item.data import loader as loader_module
from src.item.data.loader import Dataloader, _load_string_map


class _LoaderFailure(BaseException):
    pass


def test_load_string_map_returns_string_values(tmp_path):
    path = tmp_path / "strings.json"
    path.write_text(json.dumps({"first": "one", "second": "two"}), encoding="utf-8")

    assert _load_string_map(path) == {"first": "one", "second": "two"}


@pytest.mark.parametrize("payload", [[], {"first": 1}, {"first": None}])
def test_load_string_map_rejects_non_string_maps(tmp_path, payload):
    path = tmp_path / "strings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="only string keys and values"):
        _load_string_map(path)


def test_dataloader_has_expected_data_containers():
    assert isinstance(Dataloader.affix_dict, dict)
    assert isinstance(Dataloader.aspect_list, list)


def test_dataloader_does_not_publish_while_loading(monkeypatch):
    monkeypatch.setattr(Dataloader, "_instance", None)
    monkeypatch.setattr(Dataloader, "data_loaded", False)
    load_started = threading.Event()
    allow_load = threading.Event()
    second_lock_attempted = threading.Event()
    second_returned = threading.Event()
    instances = []
    second_aspect_list = []
    errors = []
    underlying_lock = threading.Lock()
    lock_enter_count = 0
    lock_enter_count_lock = threading.Lock()

    class SignalingLock:
        def __enter__(self):
            nonlocal lock_enter_count
            with lock_enter_count_lock:
                lock_enter_count += 1
                if lock_enter_count == 2:
                    second_lock_attempted.set()
            underlying_lock.acquire()
            return self

        def __exit__(self, _exc_type, _exc_value, _traceback):
            underlying_lock.release()

    def load_data(instance):
        load_started.set()
        if not allow_load.wait(timeout=2):
            message = "timed out waiting to finish loading"
            raise AssertionError(message)
        instance.affix_dict = {"ready": "yes"}
        instance.aspect_list = ["ready"]

    def construct(second=False):
        try:
            instance = Dataloader()
            instances.append(instance)
            if second:
                second_aspect_list.append(instance.aspect_list)
        except Exception as error:  # ruff:ignore[blind-except]
            errors.append(error)
        finally:
            if second:
                second_returned.set()

    monkeypatch.setattr(loader_module, "DATALOADER_LOCK", SignalingLock())
    monkeypatch.setattr(Dataloader, "load_data", load_data)
    first_thread = threading.Thread(target=construct)
    second_thread = None
    try:
        first_thread.start()
        assert load_started.wait(timeout=1)

        second_thread = threading.Thread(target=construct, kwargs={"second": True})
        second_thread.start()
        assert second_lock_attempted.wait(timeout=1)
        assert not second_returned.wait(timeout=0.1)

        allow_load.set()
        first_thread.join(timeout=2)
        second_thread.join(timeout=2)
        assert not first_thread.is_alive()
        assert not second_thread.is_alive()
        assert errors == []
        assert len(instances) == 2
        assert instances[0] is instances[1]
        assert instances[1].data_loaded is True
        assert instances[1].affix_dict == {"ready": "yes"}
        assert second_aspect_list == [["ready"]]
    finally:
        allow_load.set()
        first_thread.join(timeout=2)
        if second_thread is not None:
            second_thread.join(timeout=2)


@pytest.mark.parametrize("failure", [RuntimeError("load failed"), _LoaderFailure()])
def test_dataloader_retries_after_failed_initialization(monkeypatch, failure):
    monkeypatch.setattr(Dataloader, "_instance", None)
    monkeypatch.setattr(Dataloader, "data_loaded", False)
    attempts = 0

    def load_data(instance):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise failure
        instance.affix_dict = {"ready": "yes"}

    monkeypatch.setattr(Dataloader, "load_data", load_data)
    with pytest.raises(type(failure)):
        Dataloader()
    assert Dataloader._instance is None
    assert Dataloader.data_loaded is False

    instance = Dataloader()
    assert attempts == 2
    assert instance.data_loaded is True
    assert instance.affix_dict == {"ready": "yes"}


def test_dataloader_allows_same_thread_reentrant_access(monkeypatch):
    monkeypatch.setattr(Dataloader, "_instance", None)
    monkeypatch.setattr(Dataloader, "data_loaded", False)
    inner_instances = []
    result = []
    errors = []

    def load_data(instance):
        inner_instances.append(Dataloader())
        instance.aspect_list = ["ready"]

    def construct():
        try:
            result.append(Dataloader())
        except Exception as error:  # ruff:ignore[blind-except]
            errors.append(error)

    monkeypatch.setattr(Dataloader, "load_data", load_data)
    thread = threading.Thread(target=construct, daemon=True)
    thread.start()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert errors == []
    assert len(result) == 1
    assert inner_instances == result
    assert result[0].data_loaded is True
    assert result[0].aspect_list == ["ready"]
