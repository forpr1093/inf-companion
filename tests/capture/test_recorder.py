import numpy as np
import pytest

from inf_companion.capture.recorder import FrameRecorder


def frame(seed: int) -> np.ndarray:
    """Distinct-looking frames: random blocks, so average hashes differ a lot."""
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 256, (16, 16, 3), dtype=np.uint8)
    return np.kron(small, np.ones((4, 4, 1), np.uint8))


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def recorder(tmp_path, **kw):
    saved = []
    clock = Clock()
    rec = FrameRecorder(tmp_path, clock=clock, save=lambda img, path: saved.append(path), **kw)
    return rec, saved, clock


def test_saves_first_frame_per_screen(tmp_path):
    rec, saved, clock = recorder(tmp_path)
    rec.offer(frame(1), "music_select")
    clock.t = 5
    rec.offer(frame(2), "result")
    assert [p.parent.name for p in saved] == ["music_select", "result"]
    assert all(p.suffix == ".png" and p.parent.parent == tmp_path for p in saved)


def test_skips_similar_frames(tmp_path):
    rec, saved, clock = recorder(tmp_path)
    rec.offer(frame(1), "music_select")
    clock.t = 5
    rec.offer(frame(1), "music_select")
    clock.t = 10
    rec.offer(frame(2), "music_select")
    assert len(saved) == 2


def test_respects_interval(tmp_path):
    rec, saved, clock = recorder(tmp_path, min_interval_s=1.0)
    rec.offer(frame(1), "music_select")
    clock.t = 0.5
    rec.offer(frame(2), "music_select")
    clock.t = 1.5
    rec.offer(frame(3), "music_select")
    assert len(saved) == 2


def test_unknown_screen_saved_as_unknown(tmp_path):
    rec, saved, _ = recorder(tmp_path)
    rec.offer(frame(1), None)
    assert saved[0].parent.name == "unknown"


def test_stops_at_max_files_with_message(tmp_path):
    rec, saved, clock = recorder(tmp_path, max_files=2)
    messages = []
    for i in range(4):
        clock.t = i * 2
        messages.append(rec.offer(frame(i), "music_select"))
    assert len(saved) == 2
    assert messages[:2] == [None, None]
    assert "2" in messages[2] and messages[3] is None


def test_recorder_failure_turns_off(tmp_path):
    calls = []

    def broken(img, path):
        calls.append(path)
        raise OSError("disk full")

    clock = Clock()
    rec = FrameRecorder(tmp_path, clock=clock, save=broken)
    first = rec.offer(frame(1), "music_select")
    clock.t = 5
    second = rec.offer(frame(2), "music_select")
    assert "disk full" in first and second is None
    assert len(calls) == 1


def test_writes_real_png(tmp_path):
    from PIL import Image
    rec = FrameRecorder(tmp_path)
    rec.offer(frame(1), "result")
    files = list((tmp_path / "result").glob("*.png"))
    assert len(files) == 1 and Image.open(files[0]).size == (64, 64)


def test_cli_record_flag():
    from inf_companion.cli import parse_args
    assert parse_args(["--record", "D:/rec"]).record == "D:/rec"
    assert parse_args([]).record is None
