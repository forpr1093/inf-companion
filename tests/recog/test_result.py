from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from inf_companion.capture.base import normalise

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "tables"
RESULT = ROOT / "tests" / "fixtures" / "screens" / "result"

pytestmark = pytest.mark.skipif(not (TABLES / "details.json").is_file(),
                                reason="tables/ not converted: run uv run python tools/convert_tables.py")


@pytest.fixture(scope="module")
def reader():
    from inf_companion.recog.result import ResultReader
    from inf_companion.tables.load import load_tables
    return ResultReader(load_tables(TABLES))


def load(name):
    return normalise(Image.open(RESULT / name))


def test_reads_result_fixture(reader):
    r = reader.read(load("dxcam_max_0012.png"))
    assert (r.side, r.playmode, r.title, r.difficulty, r.level) == ("1P", "SP", "Mermaid girl", "HYPER", 8)
    assert (r.cleartype, r.cleartype_best) == ("CLEAR", "HARD CLEAR")
    assert (r.djlevel, r.djlevel_best) == ("A", "AA")
    assert (r.score, r.score_best) == (1228, 1437)
    assert (r.misscount, r.misscount_best) == (14, 8)
    assert r.judges == {"pgreat": 485, "great": 258, "good": 100, "bad": 4, "poor": 10}
    assert r.score == 2 * r.judges["pgreat"] + r.judges["great"]
    assert r.notes == 856  # matches notesradar SP HYPER
    assert r.fast is not None and r.slow is not None
    assert r.fast + r.slow <= r.judges["great"] + r.judges["good"] + r.judges["bad"] + r.judges["poor"]
    assert r.complete


def test_result_animating_is_incomplete(reader):
    r = reader.read(load("dxcam_max_0008.png"))
    assert r.side is None and not r.complete
    assert r.title == "Mermaid girl"


def test_score_needs_broadcast_packing(reader, monkeypatch):
    from inf_companion.recog import result, pack
    monkeypatch.setattr(result, "nibbles_cols", pack.nibbles)
    assert reader.read(load("dxcam_max_0012.png")).score is None


def test_black_frame_incomplete(reader):
    r = reader.read(np.zeros((1080, 1920, 3), np.uint8))
    assert not r.complete and r.title is None


def test_complete_needs_judges_that_add_up():
    from inf_companion.recog.result import ResultRead
    ok = dict(side="1P", playmode="SP", difficulty="HYPER", cleartype="CLEAR", score=1228,
              judges={"pgreat": 485, "great": 258, "good": 100, "bad": 4, "poor": 10})
    assert ResultRead(**ok).complete
    assert not ResultRead(**ok | {"score": 228}).complete
    assert not ResultRead(**ok | {"judges": ok["judges"] | {"poor": None}}).complete


def test_bad_table_turns_reading_off_not_capture():
    from inf_companion.capture.process import _make_reader
    from inf_companion.tables.load import load_tables
    tables = load_tables(TABLES)
    real = tables.raw
    tables.raw = lambda name: {} if name == "musicselect" else real(name)
    reader, notice = _make_reader(tables, "1P")
    assert reader.select is None and reader.result is not None
    assert "song select" in notice
