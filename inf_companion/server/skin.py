"""Serving images from a local skin folder, without ever leaving that folder."""

from pathlib import Path

_PARTS = {"notes": "play/parts/notes"}


def skin_root(skin_dir: str) -> Path:
    """Relative skin paths resolve against the working directory."""
    p = Path(skin_dir).expanduser()
    return p if p.is_absolute() else Path.cwd() / p


def resolve_skin_file(skin_dir: Path, rel: str) -> Path | None:
    """Return the file for `rel` only if it's a .png that really lives inside `skin_dir`."""
    if not rel or rel.startswith(("/", "\\")) or not rel.lower().endswith(".png"):
        return None
    try:
        root = skin_dir.resolve()
        path = (root / rel).resolve()
    except (OSError, RuntimeError):
        return None
    if not path.is_relative_to(root) or not path.is_file():
        return None
    return path


def list_skin(skin_dir: Path) -> dict:
    info: dict = {"available": (skin_dir / _PARTS["notes"]).is_dir()}
    for key, rel in _PARTS.items():
        folder = skin_dir / rel
        info[key] = sorted(p.stem for p in folder.glob("*.png")) if folder.is_dir() else []
    return info
