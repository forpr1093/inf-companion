import importlib.util
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

_spec = importlib.util.spec_from_file_location("capture_spike", Path(__file__).parents[2] / "tools" / "capture_spike.py")
spike = importlib.util.module_from_spec(_spec)
sys.modules["capture_spike"] = spike  # dataclasses look the module up by name
_spec.loader.exec_module(spike)
Sample, summarise, find_window, is_black = spike.Sample, spike.summarise, spike.find_window, spike.is_black


def test_black_frames_flagged():
    s = [Sample(t=i / 4, ok=True, black=True, cpu=1.0) for i in range(40)]
    assert summarise(s)["status"] == "black frames"


def test_fps_and_cpu_summary():
    s = [Sample(t=i / 4, ok=True, black=False, cpu=2.0 + i % 2) for i in range(41)]
    r = summarise(s)
    assert r["status"] == "ok" and abs(r["fps"] - 4.0) < 0.2 and r["cpu_max"] == 3.0


def test_no_frames_status():
    s = [Sample(t=i, ok=False, black=False, cpu=0.5) for i in range(5)]
    assert summarise(s)["status"] == "no frames"
    assert summarise([])["status"] == "no window"


def test_find_window_none_reports_missing():
    assert find_window(enum=lambda: [(1, "Notepad")]) is None
    assert find_window(enum=lambda: [(7, "beatmania IIDX INFINITAS")]) == 7


def test_is_black():
    assert is_black(np.zeros((4, 4, 3), np.uint8)) and not is_black(np.full((4, 4, 3), 40, np.uint8))
