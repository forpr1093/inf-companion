import json
from pathlib import Path

import numpy as np
import pytest

from inf_companion.recog.pack import (LAMPS, as_array, dominant, in_ranges, nibbles, nibbles_cols,
                                      packbits_hex, read_digits, to_index, walk)

TABLES = Path(__file__).resolve().parents[2] / "tables"


def test_to_index_slices_and_ints():
    assert to_index([{"slice": [1, 5, 2]}, 3]) == (slice(1, 5, 2), 3)
    assert to_index([{"slice": [None, 1, None]}]) == (slice(None, 1, None),)


def test_nibbles():
    assert nibbles(np.array([1, 0, 1, 1, 0, 0, 0, 1])) == "b1"
    assert nibbles(np.array([[1, 1, 1, 1], [0, 0, 1, 0]])) == "f2"


def test_nibbles_cols_broadcasts():
    ones = np.ones((2, 6), int)
    assert nibbles_cols(ones) == "ffff"
    assert nibbles(ones) == "fff"


def test_packbits_hex():
    assert packbits_hex(np.array([1] * 8 + [0] * 8)) == "ff00"


def test_walk_stops_at_str():
    trie = {"a": {"b": "Song", "c": {"d": "Other"}}}
    assert walk(trie, ["a", "b", "zzz"]) == "Song"
    assert walk(trie, ["a", "c", "d"]) == "Other"
    assert walk(trie, ["a", "x"]) is None
    assert walk(trie, ["a"]) is None


def test_in_ranges():
    img = np.array([[[10, 20, 30], [11, 20, 30], [10, 19, 30]]], np.uint8)
    assert in_ranges(img, [[10, 10], [20, 25], [0, 255]]).tolist() == [[True, False, False]]


def test_dominant_first_max():
    assert dominant(np.array([5, 3, 5, 3, 9])) == 3
    assert dominant(np.array([[7, 7, 1]])) == 7


def test_as_array():
    a = as_array({"array": [[1, 2], [3, 4]], "dtype": "|u1", "shape": [2, 2]})
    assert a.dtype == np.uint8 and a.tolist() == [[1, 2], [3, 4]]


def test_read_digits_right_to_left_stops_on_unknown():
    # 4 parts of width 2; a part is "on" where pixels equal 9. Keys: packbits of the part.
    table = {packbits_hex(np.array([1, 0])): 1, packbits_hex(np.array([0, 1])): 2}
    field = np.array([[0, 0, 0, 0, 9, 0, 0, 9]])  # parts: blank, blank, "1", "2"
    read = lambda f: read_digits(f, 4, (0, slice(None)), 9, table, packbits_hex)
    assert read(field) == 12
    assert read(np.zeros((1, 8), int)) is None


def test_lamps_use_official_names():
    assert LAMPS["H-CLEAR"] == "HARD CLEAR"
    assert LAMPS["EXH-CLEAR"] == "EX HARD CLEAR"
    assert LAMPS["F-COMBO"] == "FULLCOMBO CLEAR"
    assert LAMPS["CLEAR"] == "CLEAR" and LAMPS["NO PLAY"] == "NO PLAY"


@pytest.mark.skipif(not (TABLES / "details.json").is_file(), reason="tables/ not converted")
def test_every_table_lamp_maps():
    names = set(json.loads((TABLES / "details.json").read_text(encoding="utf-8"))["clear_type"].values())
    names |= set(json.loads((TABLES / "musicselect.json").read_text(encoding="utf-8"))["cleartype"]["table"].values())
    assert names <= set(LAMPS)
