import pytest
from starlette.testclient import TestClient

from inf_companion.events import EventBus
from inf_companion.server.app import AppContext, create_app
from inf_companion.storage.db import BindingsRepo, SettingsRepo, open_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@pytest.fixture
def ctx(tmp_path):
    conn = open_db(tmp_path / "c.sqlite3")
    return AppContext(
        bus=EventBus(), settings=SettingsRepo(conn), bindings=BindingsRepo(conn),
        data_dir=tmp_path, static_dir=None, input=None,
    )


@pytest.fixture
def client(ctx):
    with TestClient(create_app(ctx)) as c:
        yield c


@pytest.fixture
def skin(tmp_path):
    root = tmp_path / "skin"
    for rel in ["play/parts/notes/default.png", "play/parts/frame/Wide/SpaceShip.png", "play/parts/laser/defalut.png"]:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(PNG)
    (root / "play/parts/notes/readme.lua").write_text("x")
    return root


@pytest.fixture
def client_with_skin(ctx, skin):
    ctx.settings.update({"skin_dir": str(skin)})
    with TestClient(create_app(ctx)) as c:
        yield c
