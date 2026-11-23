from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from inf_companion.capture.base import normalise

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "tables"
SELECT = sorted((ROOT / "tests" / "fixtures" / "screens" / "music_select").glob("*.png"))

pytestmark = pytest.mark.skipif(not (TABLES / "musicselect.json").is_file(),
                                reason="tables/ not converted: run uv run python tools/convert_tables.py")


@pytest.fixture(scope="module")
def reader():
    from inf_companion.recog.select import SelectReader
    from inf_companion.tables.load import load_tables
    return SelectReader(load_tables(TABLES))


def load(path):
    return normalise(Image.open(path))


@pytest.mark.parametrize("path", SELECT, ids=lambda p: p.name)
def test_reads_every_select_fixture(reader, path):
    from inf_companion.recog.select import SelectRead
    assert reader.read(load(path)) == SelectRead("SP", "Mermaid girl", "HYPER", 8, "HARD CLEAR", "AA", 1437, 8)


def test_black_frame_reads_nothing(reader):
    from inf_companion.recog.select import SelectRead
    assert reader.read(np.zeros((1080, 1920, 3), np.uint8)) == SelectRead(*[None] * 8)


def test_bgr_frame_does_not_read_playmode(reader):
    assert reader.read(load(SELECT[0])[:, :, ::-1].copy()).playmode is None


def test_missing_table_raises(tmp_path):
    from inf_companion.recog.select import SelectReader
    from inf_companion.tables.load import TablesError, load_tables
    tables = load_tables(TABLES)
    tables.dir = tmp_path  # raw() reads from here: musicselect.json is absent
    with pytest.raises(TablesError, match="musicselect"):
        SelectReader(tables)
