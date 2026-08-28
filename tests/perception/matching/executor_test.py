from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread

import numpy as np

from src.perception.matching import SearchConfig
from src.perception.matching.executor import find_matches_for_templates
from src.perception.matching.models import ImageMatch
from src.settings import Template


def test_first_parallel_result_does_not_wait_for_a_slower_worker() -> None:
    slow_started = Event()
    release_slow = Event()
    slow_template = Template(name="slow")
    fast_template = Template(name="fast")

    def find_template_matches(template, *_args, **_kwargs):
        if template is slow_template:
            slow_started.set()
            assert release_slow.wait(timeout=1)
            return []
        assert slow_started.wait(timeout=1)
        return [ImageMatch(region=(0, 0, 1, 1), score=0.9)]

    executor = ThreadPoolExecutor(max_workers=2)
    result_holder: list[list[list[ImageMatch]]] = []
    finished = Event()

    def run_search() -> None:
        result_holder.append(
            find_matches_for_templates(
                [slow_template, fast_template],
                np.zeros((2, 2, 3), dtype=np.uint8),
                SearchConfig(mode="first"),
                None,
                None,
                executor,
                find_template_matches,
            )
        )
        finished.set()

    search_thread = Thread(target=run_search)
    search_thread.start()
    try:
        assert slow_started.wait(timeout=1)
        assert finished.wait(timeout=1)
    finally:
        release_slow.set()
        search_thread.join(timeout=1)
        executor.shutdown(wait=True)

    assert result_holder == [[[], [ImageMatch(region=(0, 0, 1, 1), score=0.9)]]]
