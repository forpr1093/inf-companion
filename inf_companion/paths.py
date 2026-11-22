"""Where the app keeps its data. Everything is configurable so nothing has to live on C:."""

import os
from collections.abc import Mapping
from pathlib import Path

ENV_DATA_DIR = "INF_COMPANION_DATA"


def resolve_data_dir(arg: str | None, env: Mapping[str, str] = os.environ) -> Path:
    """Pick the data folder (argument, then env var, then ./data), create it, return it absolute."""
    if arg:
        chosen = Path(arg)
    elif env.get(ENV_DATA_DIR):
        chosen = Path(env[ENV_DATA_DIR])
    else:
        chosen = Path.cwd() / "data"
    path = chosen.expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
