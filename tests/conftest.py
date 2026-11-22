import pytest
from starlette.testclient import TestClient

from inf_companion.events import EventBus
from inf_companion.server.app import AppContext, create_app
from inf_companion.storage.db import BindingsRepo, SettingsRepo, open_db



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
