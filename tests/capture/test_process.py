import numpy as np

from inf_companion.capture.process import RATE_FPS, StableScreen, capture_loop, start_capture


class StopAfter:
    def __init__(self, n):
        self.n = n

    def is_set(self):
        self.n -= 1
        return self.n < 0


class FakeSource:
    def __init__(self, frames):
        self.frames = list(frames)

    def grab(self):
        return self.frames.pop(0) if self.frames else None

    def close(self):
        pass


def frames(labels):
    """One tiny frame per label; the classifier reads the label back from pixel [0, 0, 0]."""
    codes = {"a": 1, "p": 2}
    return [np.full((1, 1, 3), codes[x], np.uint8) for x in labels]


def classify(frame):
    return {1: "music_select", 2: "play"}[int(frame[0, 0, 0])]


def run(labels, iterations):
    emitted, sleeps = [], []
    capture_loop(FakeSource(frames(labels)), classify, emitted.append, StopAfter(iterations),
                 clock=lambda: 0.0, sleep=sleeps.append)
    return emitted, sleeps


def test_stable_screen_needs_three_in_a_row():
    s = StableScreen(3)
    assert [s.feed(x) for x in "aabbbb"] == [None, None, None, None, "b", None]


def test_emits_screen_change_once():
    emitted, _ = run("aaappp", 6)
    screens = [e["screen"] for e in emitted if e["type"] == "screen"]
    assert screens == ["music_select", "play"]
    assert emitted[0] == {"type": "capture_status", "state": "running"}


def test_rate_follows_screen():
    _, sleeps = run("aaappp", 6)
    assert sleeps[:3] == [1 / RATE_FPS["default"]] * 3      # 0.25 s on menus
    assert sleeps[-1] == 1 / RATE_FPS["play"]                # 0.5 s once play is stable


def test_capture_loop_idles_without_frames():
    emitted, sleeps = run("", 5)
    assert emitted == [{"type": "capture_status", "state": "no frames"}]
    assert sleeps == [1.0] * 5


class RecordingBus:
    def __init__(self):
        self.events = []

    def publish(self, e):
        self.events.append(e)


def test_app_runs_without_tables(tmp_path):
    bus = RecordingBus()
    handle = start_capture("replay", tmp_path, tmp_path / "no-tables", "1P", bus)
    assert handle.process is None
    off = [e for e in bus.events if e["type"] == "capture_status"][-1]
    assert off["state"] == "off" and "convert_tables.py" in off["message"]
    assert handle.state() == {"screen": None, "capture_status": {"state": "off", "message": off["message"]},
                              "chart": None, "personal_best": None}
    handle.stop()  # safe when nothing was started


def test_running_status_carries_notice():
    emitted = []
    capture_loop(FakeSource(frames("a")), classify, emitted.append, StopAfter(1),
                 clock=lambda: 0.0, sleep=lambda s: None, notice="no play reference for 2P")
    assert emitted[0] == {"type": "capture_status", "state": "running", "message": "no play reference for 2P"}


def write_min_tables(d):
    import json
    files = {"manifest": {"source": "kaktuswald/inf-notebook", "commit": "abc", "files": {}},
             "screenrecognition": {"get_screen": {}}, "musictable": {}, "notesradar": {}}
    for name, data in files.items():
        (d / f"{name}.json").write_text(json.dumps(data))


def test_child_crash_is_reported(tmp_path):
    import time
    write_min_tables(tmp_path)
    bus = RecordingBus()
    handle = start_capture("replay", tmp_path / "missing-source", tmp_path, "1P", bus)
    handle.process.join(timeout=20)
    handle._relay.join(timeout=5)
    assert handle.status["state"] == "off"
    assert "missing-source" in handle.status["message"]
    handle.stop()


def test_child_exit_without_message_is_reported():
    from inf_companion.capture.process import exit_status
    assert exit_status(1, {"state": "running"}) == {"state": "off", "message": "capture process exited (code 1)"}
    assert exit_status(0, {"state": "running"}) is None
    assert exit_status(1, {"state": "off", "message": "x"}) is None


def test_capture_loop_forwards_on_frame_messages():
    emitted, seen = [], []

    def on_frame(frame, screen):
        seen.append(screen)
        return [{"type": "chart", "chart": {"title": "x"}}] if screen == "music_select" else []

    capture_loop(FakeSource(frames("aaa")), classify, emitted.append, StopAfter(3),
                 clock=lambda: 0.0, sleep=lambda s: None, on_frame=on_frame)
    assert seen == [None, None, "music_select"]
    assert emitted[-1] == {"type": "chart", "chart": {"title": "x"}}


def test_handle_keeps_last_chart_best_and_result():
    from inf_companion.capture.process import CaptureHandle
    h = CaptureHandle()
    h.remember({"type": "chart", "chart": {"title": "x"}})
    h.remember({"type": "personal_best", "best": None})
    h.remember({"type": "result", "result": {"score": 1}})
    assert h.state()["chart"] == {"title": "x"} and h.state()["personal_best"] is None
    assert h.result == {"score": 1}


def test_on_message_sees_every_message_and_cant_break_capture(tmp_path):
    class Bus:
        def __init__(self):
            self.events = []

        def publish(self, e):
            self.events.append(e)

    seen = []

    def listener(msg):
        seen.append(msg["type"])
        raise RuntimeError("database locked")

    bus = Bus()
    start_capture("replay", tmp_path, tmp_path / "no-tables", "1P", bus, on_message=listener)
    assert seen == ["capture_status"]
    assert bus.events[-1]["type"] == "capture_status"
