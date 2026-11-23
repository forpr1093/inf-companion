import json

import pytest

from inf_companion.tables.load import TablesError, load_tables


def write_tables(d, **override):
    files = {
        "manifest": {"source": "kaktuswald/inf-notebook", "commit": "abc", "files": {}},
        "screenrecognition": {"get_screen": {"result": {"area": {"left": 1, "top": 2, "width": 3, "height": 4}, "value": 9}}},
        "musictable": {"musics": {}},
        "notesradar": {"SP": {}},
        "deeper": {"x": 1},
    } | override
    for name, data in files.items():
        if data is not None:
            (d / f"{name}.json").write_text(json.dumps(data))


def test_loads_minimal_tables(tmp_path):
    write_tables(tmp_path)
    t = load_tables(tmp_path)
    assert t.screen["get_screen"]["result"]["value"] == 9
    assert t.notesradar == {"SP": {}} and t.manifest["commit"] == "abc"
    assert t.raw("deeper") == {"x": 1}


def test_missing_tables_reported(tmp_path):
    with pytest.raises(TablesError, match="screenrecognition.json is missing.*convert_tables.py"):
        load_tables(tmp_path)


def test_missing_folder_reported(tmp_path):
    with pytest.raises(TablesError, match="No tables folder"):
        load_tables(tmp_path / "nope")


def test_malformed_json_reported(tmp_path):
    write_tables(tmp_path)
    (tmp_path / "musictable.json").write_text("{not json")
    with pytest.raises(TablesError, match="musictable.json is not valid JSON"):
        load_tables(tmp_path)


def test_raw_missing_optional_table(tmp_path):
    write_tables(tmp_path)
    with pytest.raises(TablesError, match="details.json is missing"):
        load_tables(tmp_path).raw("details")


@pytest.mark.parametrize("entry,bad", [
    ({"value": 9}, "area"),
    ({"area": {"left": 1, "top": 2, "width": 3}, "value": 9}, "area"),
    ({"area": {"left": 1, "top": 2, "width": 3, "height": 4}, "value": "9"}, "value"),
])
def test_bad_screen_table_shape_reported(tmp_path, entry, bad):
    write_tables(tmp_path, screenrecognition={"get_screen": {"result": entry}})
    with pytest.raises(TablesError, match=f"screenrecognition.*result.*{bad}.*convert_tables.py"):
        load_tables(tmp_path)


def test_missing_get_screen_reported(tmp_path):
    write_tables(tmp_path, screenrecognition={"something_else": {}})
    with pytest.raises(TablesError, match="screenrecognition.*get_screen"):
        load_tables(tmp_path)


def test_unknown_source_reported(tmp_path):
    write_tables(tmp_path, manifest={"source": "someone/else", "commit": "abc", "files": {}})
    with pytest.raises(TablesError, match="unknown source.*someone/else"):
        load_tables(tmp_path)
