import numpy as np
import pytest
from PIL import Image

from inf_companion.capture.base import normalise
from inf_companion.capture.replay import ReplaySource


def test_normalise_resizes_to_1080p():
    img = Image.new("RGBA", (1600, 900), (10, 20, 30, 255))
    out = normalise(img)
    assert out.shape == (1080, 1920, 3) and out.dtype == np.uint8
    assert tuple(out[500, 900]) == (10, 20, 30)


def test_normalise_bgr_array():
    bgr = np.zeros((1080, 1920, 3), np.uint8)
    bgr[..., 0] = 200  # blue in BGR
    out = normalise(bgr, bgr=True)
    assert tuple(out[0, 0]) == (0, 0, 200)


def _write(folder, names):
    for i, n in enumerate(names):
        Image.new("RGB", (1920, 1080), (i * 10, 0, 0)).save(folder / f"{n}.png")


def test_replay_plays_folder_in_order_then_none(tmp_path):
    _write(tmp_path, ["2", "10", "1"])  # created order: 2 -> red 0, 10 -> 10, 1 -> 20
    src = ReplaySource(tmp_path)
    reds = [int(src.grab()[0, 0, 0]) for _ in range(3)]
    assert reds == [20, 0, 10]  # natural order 1, 2, 10
    assert src.grab() is None and len(src) == 3


def test_replay_loop(tmp_path):
    _write(tmp_path, ["a", "b"])
    src = ReplaySource(tmp_path, loop=True)
    assert all(src.grab() is not None for _ in range(5))


def test_replay_single_image(tmp_path):
    _write(tmp_path, ["only"])
    src = ReplaySource(tmp_path / "only.png")
    assert src.grab() is not None and src.grab() is None


def test_replay_missing_source_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="No replay frames"):
        ReplaySource(tmp_path / "nope")
    with pytest.raises(FileNotFoundError, match="No replay frames"):
        ReplaySource(tmp_path)  # empty folder
