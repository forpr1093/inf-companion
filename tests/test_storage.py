import pytest

from inf_companion.input.model import Binding, KeyEvent, RawEvent, Source, TARGETS
from inf_companion.settings import DEFAULT_SETTINGS, validate_settings_patch
from inf_companion.storage.db import BindingsRepo, SettingsRepo, open_db


def test_defaults_then_update_persists(tmp_path):
    conn = open_db(tmp_path / "c.sqlite3")
    s = SettingsRepo(conn)
    assert s.get_all() == DEFAULT_SETTINGS
    assert s.update({"side": "2P"})["side"] == "2P"
    assert SettingsRepo(open_db(tmp_path / "c.sqlite3")).get_all()["side"] == "2P"


@pytest.mark.parametrize(
    "patch",
    [{"side": "3P"}, {"manual_bpm": 0}, {"beats_per_loop": 1.5}, {"nope": 1}, {"skin_dir": "skins/WMII_FHD"}, {"skin_notes": "default"},
     {"manual_bpm": True}, {"beats_per_loop": "4"}],
)
def test_invalid_patch_rejected_and_nothing_stored(tmp_path, patch):
    s = SettingsRepo(open_db(tmp_path / "c.sqlite3"))
    with pytest.raises(ValueError):
        s.update(patch)
    assert s.get_all() == DEFAULT_SETTINGS


def test_settings_keys_are_trimmed():
    assert set(DEFAULT_SETTINGS) == {"side", "manual_bpm", "beats_per_loop", "theme"}


def test_legacy_stored_key_is_ignored(tmp_path):
    conn = open_db(tmp_path / "c.sqlite3")
    conn.execute("INSERT INTO settings (key, value) VALUES ('skin_frame', '\"SpaceShip\"')")
    conn.commit()
    assert "skin_frame" not in SettingsRepo(conn).get_all()


@pytest.mark.parametrize("patch", [{"orientation": "auto"}, {"skin_frame": "SpaceShip"}])
def test_removed_settings_rejected(tmp_path, patch):
    with pytest.raises(ValueError):
        SettingsRepo(open_db(tmp_path / "c.sqlite3")).update(patch)


def test_partial_invalid_patch_stores_nothing(tmp_path):
    s = SettingsRepo(open_db(tmp_path / "c.sqlite3"))
    with pytest.raises(ValueError):
        s.update({"side": "2P", "manual_bpm": -1})
    assert s.get_all()["side"] == "1P"


def test_binding_round_trip(tmp_path):
    b = Binding("g1", "Pad", {"1": Source("button", 0), "S_up": Source("axis", 0, sign=1), "S_down": Source("axis", 0, sign=-1)})
    r = BindingsRepo(open_db(tmp_path / "c.sqlite3"))
    r.put(b)
    assert r.get("g1") == b and r.all() == {"g1": b}
    assert r.get("nope") is None


def test_binding_json_round_trip():
    b = Binding("g1", "Pad", {"7": Source("hat", 0, mask=4)})
    assert Binding.from_json(b.to_json()) == b
    assert b.to_json()["map"]["7"] == {"kind": "hat", "index": 0, "sign": 0, "mask": 4}


def test_reopen_does_not_rerun_migrations(tmp_path):
    open_db(tmp_path / "c.sqlite3").close()
    conn = open_db(tmp_path / "c.sqlite3")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2


def test_model_basics():
    assert TARGETS == ("1", "2", "3", "4", "5", "6", "7", "S_up", "S_down")
    assert KeyEvent("S", True, 1.0, "up").dir == "up"
    assert RawEvent("g", "button", 0, 1, 0.0).kind == "button"


@pytest.mark.parametrize(
    "patch, message",
    [({"manual_bpm": 0}, "BPM must be between 30 and 999."),
     ({"beats_per_loop": 0}, "Beats per loop must be a whole number from 1 to 64."),
     ({"side": "3P"}, "Side must be 1P or 2P.")],
)
def test_validation_messages_are_plain(patch, message):
    with pytest.raises(ValueError, match=message.replace(".", r"\.")):
        validate_settings_patch(patch)


def _result(score=1228, title="Mermaid girl", pgreat=485):
    return {"side": "1P", "playmode": "SP", "title": title, "difficulty": "HYPER", "level": 8, "notes": 856,
            "cleartype": "CLEAR", "djlevel": "A", "score": score, "misscount": 14,
            "judges": {"pgreat": pgreat, "great": score - 2 * pgreat, "good": 100, "bad": 4, "poor": 10},
            "fast": 120, "slow": 80}


def test_plays_recent_newest_first_and_persist(tmp_path):
    from datetime import datetime, timedelta, timezone
    from inf_companion.storage.db import PlaysRepo
    t0 = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
    plays = PlaysRepo(open_db(tmp_path / "c.sqlite3"))
    assert plays.add(_result(1228), played_at=t0)
    assert plays.add(_result(1300, title=None), played_at=t0 + timedelta(minutes=3))
    again = PlaysRepo(open_db(tmp_path / "c.sqlite3")).recent()
    assert again == [
        {"title": "Unknown title", "difficulty": "HYPER", "level": 8, "score": 1300, "notes": 856, "option": None,
         "played_at": (t0 + timedelta(minutes=3)).isoformat()},
        {"title": "Mermaid girl", "difficulty": "HYPER", "level": 8, "score": 1228, "notes": 856, "option": None,
         "played_at": t0.isoformat()},
    ]


def test_plays_same_result_twice_in_a_row_is_stored_once(tmp_path):
    from datetime import datetime, timedelta, timezone
    from inf_companion.storage.db import PlaysRepo
    t0 = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
    plays = PlaysRepo(open_db(tmp_path / "c.sqlite3"))
    assert plays.add(_result(), played_at=t0)
    assert not plays.add(_result(), played_at=t0 + timedelta(seconds=20))
    assert plays.add(_result(), played_at=t0 + timedelta(minutes=10))  # replayed later: a new play
    assert len(plays.recent()) == 2


def test_plays_recent_limit(tmp_path):
    from inf_companion.storage.db import PlaysRepo
    plays = PlaysRepo(open_db(tmp_path / "c.sqlite3"))
    for i in range(5):
        plays.add(_result(1000 + 2 * i))
    assert [p["score"] for p in plays.recent(limit=3)] == [1008, 1006, 1004]
