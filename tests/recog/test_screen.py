from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from inf_companion.capture.base import normalise
from inf_companion.recog.screen import area_key, average_hash, classify, hamming, is_play

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "screens"
TABLES = ROOT / "tables"

needs_tables = pytest.mark.skipif(
    not (TABLES / "screenrecognition.json").is_file(),
    reason="tables/ not converted: run uv run python tools/convert_tables.py",
)


def labelled_fixtures():
    return [pytest.param(p, p.parent.name, id=f"{p.parent.name}/{p.name}")
            for p in sorted(FIXTURES.glob("*/*.png"))]


def label_to_screen(label: str) -> str:
    return "play" if label.startswith("play_") else ("unknown" if label == "other" else label)


def label_side(label: str) -> str:
    return "2P" if label == "play_2p" else "1P"


@pytest.fixture(scope="module")
def tables():
    from inf_companion.tables.load import load_tables
    return load_tables(TABLES)


def load(path) -> np.ndarray:
    return normalise(Image.open(path))


def test_fixtures_present():
    labels = {p.parent.name for p in FIXTURES.glob("*/*.png")}
    assert {"music_select", "result", "play_1p"} <= labels


@needs_tables
@pytest.mark.parametrize("path,label", labelled_fixtures())
def test_classify_fixture(path, label, tables):
    assert classify(load(path), tables, label_side(label)) == label_to_screen(label)


@needs_tables
@pytest.mark.parametrize("label", ["music_select", "result", "play_1p"])
def test_classify_downscaled_fixture(label, tables):
    path = sorted((FIXTURES / label).glob("*.png"))[0]
    small = Image.open(path).convert("RGB").resize((1600, 900), Image.BILINEAR)
    assert classify(normalise(small), tables, "1P") == label_to_screen(label)


@needs_tables
def test_black_frame_is_unknown(tables):
    assert classify(np.zeros((1080, 1920, 3), np.uint8), tables, "1P") == "unknown"


def test_play_needs_a_reference_for_the_side():
    frame = load(sorted((FIXTURES / "play_1p").glob("*.png"))[0])
    assert is_play(frame, "1P")
    assert not is_play(frame, "2P")   # no 2P reference yet


def test_area_key_orientation():
    frame = np.zeros((2, 3, 3), np.uint8)
    frame[0, 0] = (1, 2, 3)      # top row
    frame[1, 0] = (10, 20, 30)   # bottom row
    area = {"left": 0, "top": 0, "width": 2, "height": 1}
    assert area_key(frame, area, "as_is") == 6
    assert area_key(frame, area, "flipped") == 60


def test_average_hash_shape_and_distance():
    img = np.zeros((32, 32, 3), np.uint8)
    img[:, 16:] = 255
    h = average_hash(img)
    assert len(h) == 64
    assert hamming(h, h) == 0
    assert hamming(h, average_hash(255 - img)) == 256


def test_play_reference_notice():
    from inf_companion.recog.screen import play_reference_notice
    assert play_reference_notice("1P") is None
    msg = play_reference_notice("2P")
    assert "2P" in msg and "calibrate_screens.py" in msg
