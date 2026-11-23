import numpy as np
import pytest

from inf_companion.capture.dxcam_source import DxcamSource
from inf_companion.capture.win32 import crop_to_client, pick_window

MON_A = (0, 0, 1920, 1080)
MON_B = (1920, 0, 3840, 1080)


class FakeCam:
    def __init__(self, frames):
        self.frames, self.released = list(frames), False

    def grab(self):
        f = self.frames.pop(0) if self.frames else None
        if isinstance(f, Exception):
            raise f
        return f

    def release(self):
        self.released = True


class FakeWin:
    """Stands in for the Windows calls: one window, which can move, minimise or vanish."""

    def __init__(self):
        self.hwnd, self.client, self.hmon, self.monitor = 7, MON_A, 1, MON_A
        self.cams, self.made = [], []

    def find(self):
        return self.hwnd

    def client_rect(self, hwnd):
        return self.client

    def monitor_of(self, hwnd):
        return self.hmon, self.monitor

    def make_camera(self, hmon):
        cam = self.cams.pop(0)
        self.made.append((hmon, cam))
        return cam


def bgra(value, w=1920, h=1080):
    f = np.zeros((h, w, 4), np.uint8)
    f[..., 0], f[..., 1], f[..., 2] = value, value + 1, value + 2  # B, G, R
    return f


def source(win):
    return DxcamSource(find=win.find, client_rect=win.client_rect, monitor_of=win.monitor_of,
                       make_camera=win.make_camera, clock=lambda: 0.0)


def test_grab_converts_bgra_to_rgb_1080p():
    win = FakeWin()
    win.cams = [FakeCam([bgra(10)])]
    frame = source(win).grab()
    assert frame.shape == (1080, 1920, 3) and frame.dtype == np.uint8
    assert tuple(frame[0, 0]) == (12, 11, 10)


def test_unchanged_screen_repeats_last_frame():
    win = FakeWin()
    win.cams = [FakeCam([bgra(10), None, None])]
    s = source(win)
    first = s.grab()
    assert s.grab() is not None and np.array_equal(s.grab(), first)


def test_no_window_gives_none_and_no_camera():
    win = FakeWin()
    win.hwnd = None
    assert source(win).grab() is None
    assert win.made == []


def test_minimised_window_gives_none():
    win = FakeWin()
    win.cams = [FakeCam([bgra(10)])]
    win.client = (0, 0, 0, 0)
    assert source(win).grab() is None


def test_crops_to_window_on_second_monitor_and_rescales():
    win = FakeWin()
    win.hmon, win.monitor = 2, MON_B
    win.client = (1920 + 160, 90, 1920 + 160 + 1600, 90 + 900)   # 1600x900 window
    full = bgra(0)
    full[90:990, 160:1760, :3] = 200
    win.cams = [FakeCam([full])]
    frame = source(win).grab()
    assert frame.shape == (1080, 1920, 3)
    assert frame.min() == 200
    assert win.made[0][0] == 2


def test_moving_to_another_monitor_recreates_camera():
    win = FakeWin()
    a, b = FakeCam([bgra(10)]), FakeCam([bgra(20)])
    win.cams = [a, b]
    s = source(win)
    s.grab()
    win.hmon, win.monitor, win.client = 2, MON_B, MON_B
    assert tuple(s.grab()[0, 0]) == (22, 21, 20)
    assert a.released and [h for h, _ in win.made] == [1, 2]


def test_camera_error_recreates_on_next_grab():
    win = FakeWin()
    a, b = FakeCam([RuntimeError("access lost")]), FakeCam([bgra(30)])
    win.cams = [a, b]
    s = source(win)
    assert s.grab() is None
    assert a.released
    assert tuple(s.grab()[0, 0]) == (32, 31, 30)


def test_window_closed_drops_last_frame():
    win = FakeWin()
    win.cams = [FakeCam([bgra(10)])]
    s = source(win)
    s.grab()
    win.hwnd = None
    assert s.grab() is None


def test_window_lookup_is_throttled():
    win = FakeWin()
    win.hwnd = None
    calls = []
    now = [0.0]
    s = DxcamSource(find=lambda: calls.append(1), client_rect=win.client_rect, monitor_of=win.monitor_of,
                    make_camera=win.make_camera, clock=lambda: now[0])
    s.grab(); s.grab()
    now[0] = 2.5
    s.grab()
    assert len(calls) == 2


def test_close_releases_camera():
    win = FakeWin()
    cam = FakeCam([bgra(1)])
    win.cams = [cam]
    s = source(win)
    s.grab()
    s.close()
    assert cam.released


def test_pick_window_matches_title_prefix():
    windows = [(1, "Explorer"), (2, "beatmania IIDX INFINITAS"), (3, "beatmania IIDX INFINITAS (2)")]
    assert pick_window(windows) == 2
    assert pick_window([(1, "Explorer")]) is None


def test_crop_to_client_outside_monitor_is_none():
    assert crop_to_client(np.zeros((10, 10, 3), np.uint8), (20, 20, 30, 30), (0, 0, 10, 10)) is None


def test_default_capture_is_dxcam_only_on_windows():
    from inf_companion.cli import default_capture, parse_args
    assert default_capture("win32") == "dxcam"
    assert default_capture("darwin") == "off"
    assert parse_args(["--capture", "replay", "--source", "x"]).capture == "replay"


def test_replay_fps_must_be_positive():
    from inf_companion.cli import parse_args
    with pytest.raises(SystemExit):
        parse_args(["--replay-fps", "-1"])


def test_dxcam_recovery_warnings_are_quiet():
    import logging
    from inf_companion.capture.dxcam_source import quiet_dxcam_logs
    quiet_dxcam_logs()
    assert not logging.getLogger("dxcam.core.dxgi_duplicator").isEnabledFor(logging.WARNING)
    assert logging.getLogger("dxcam.dxcam").isEnabledFor(logging.ERROR)
