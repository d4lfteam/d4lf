from src.perception import TemplateMatchTrace
from src.tools.replay.diagnostics import _trace_label


def test_trace_label_identifies_trace() -> None:
    trace = TemplateMatchTrace(name="x", center=(1, 2), region=[0, 0, 1, 1], confidence=0.5)
    assert "x" in _trace_label(trace)
