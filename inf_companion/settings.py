"""User settings: defaults and validation. Stored as JSON values in SQLite."""

from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "side": "1P",
    "manual_bpm": 150,
    "beats_per_loop": 4,
    "theme": "dark",
}



def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check(key: str, v: Any) -> bool:
    if key == "side":
        return v in ("1P", "2P")
    if key == "manual_bpm":
        return _is_number(v) and 30 <= v <= 999
    if key == "beats_per_loop":
        return isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 64
    if key == "theme":
        return v in ("dark", "light")
    return False


def validate_settings_patch(patch: dict) -> dict:
    """Return the patch if every key is known and every value valid, else raise ValueError."""
    if not isinstance(patch, dict):
        raise ValueError("settings patch must be an object")
    for key, value in patch.items():
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"unknown setting: {key}")
        if not _check(key, value):
            raise ValueError(f"invalid value for {key}: {value!r}")
    return dict(patch)
