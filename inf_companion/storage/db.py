"""SQLite storage for settings and controller bindings."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
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
]


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
