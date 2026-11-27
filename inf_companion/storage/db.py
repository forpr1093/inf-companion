"""SQLite storage for settings, controller bindings and plays."""

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from inf_companion.input.model import Binding
from inf_companion.settings import DEFAULT_SETTINGS, validate_settings_patch

_MIGRATIONS = [
    """
    CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE bindings (
        device_guid TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        map TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE plays (
        id INTEGER PRIMARY KEY,
        played_at TEXT NOT NULL,
        side TEXT,
        title TEXT,
        difficulty TEXT NOT NULL,
        level INTEGER,
        notes INTEGER,
        score INTEGER NOT NULL,
        lamp TEXT NOT NULL,
        dj_level TEXT,
        miss_count INTEGER,
        judges TEXT NOT NULL,
        fast INTEGER,
        slow INTEGER
    );
    CREATE INDEX plays_played_at ON plays (played_at);
    """,
]

# The same result read again within this time is the same play (e.g. the screen label
# flickered and the result screen was read twice).
SAME_PLAY_WINDOW = timedelta(minutes=5)


def open_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for i, script in enumerate(_MIGRATIONS[version:], start=version + 1):
        with conn:
            conn.executescript(script)
            conn.execute(f"PRAGMA user_version = {i}")
    return conn


class SettingsRepo:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._lock = threading.Lock()

    def get_all(self) -> dict:
        with self._lock:
            rows = self._conn.execute("SELECT key, value FROM settings").fetchall()
        stored = {k: json.loads(v) for k, v in rows if k in DEFAULT_SETTINGS}
        return {**DEFAULT_SETTINGS, **stored}

    def update(self, patch: dict) -> dict:
        valid = validate_settings_patch(patch)
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                [(k, json.dumps(v)) for k, v in valid.items()],
            )
        return self.get_all()


class BindingsRepo:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._lock = threading.Lock()

    def all(self) -> dict[str, Binding]:
        with self._lock:
            rows = self._conn.execute("SELECT device_guid, name, map FROM bindings").fetchall()
        return {g: Binding.from_json({"device_guid": g, "name": n, "map": json.loads(m)}) for g, n, m in rows}

    def get(self, guid: str) -> Binding | None:
        return self.all().get(guid)

    def put(self, binding: Binding) -> None:
        data = binding.to_json()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO bindings (device_guid, name, map, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(device_guid) DO UPDATE SET name = excluded.name, map = excluded.map, "
                "updated_at = excluded.updated_at",
                (binding.device_guid, binding.name, json.dumps(data["map"]), datetime.now(timezone.utc).isoformat()),
            )


class PlaysRepo:
    """Plays read from result screens. Rows are kept forever; the page shows the newest."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._lock = threading.Lock()

    def add(self, result: dict, played_at: datetime | None = None) -> bool:
        """Store a result. False when it repeats the last stored play (not a new play)."""
        played_at = played_at or datetime.now(timezone.utc)
        judges = json.dumps(result.get("judges") or {}, sort_keys=True)
        key = (result.get("title"), result.get("difficulty"), result.get("score"), judges)
        with self._lock, self._conn:
            last = self._conn.execute(
                "SELECT title, difficulty, score, judges, played_at FROM plays ORDER BY id DESC LIMIT 1").fetchone()
            if last is not None and tuple(last[:4]) == key and \
                    played_at - datetime.fromisoformat(last[4]) < SAME_PLAY_WINDOW:
                return False
            self._conn.execute(
                "INSERT INTO plays (played_at, side, title, difficulty, level, notes, score, lamp, dj_level, "
                "miss_count, judges, fast, slow) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (played_at.isoformat(), result.get("side"), result.get("title"), result["difficulty"],
                 result.get("level"), result.get("notes"), result["score"], result["cleartype"],
                 result.get("djlevel"), result.get("misscount"), judges, result.get("fast"), result.get("slow")),
            )
        return True

    def recent(self, limit: int = 20) -> list[dict]:
        """The newest plays, shaped for the page's Recent plays panel."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT title, difficulty, level, score, notes, played_at FROM plays ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
        return [{"title": t or "Unknown title", "difficulty": d, "level": lv, "score": sc, "notes": n,
                 "option": None, "played_at": at} for t, d, lv, sc, n, at in rows]
