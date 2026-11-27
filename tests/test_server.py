from inf_companion.events import make_event
from inf_companion.input.model import TARGETS


def test_ws_hello_then_bus_events(client, ctx):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello" and hello["settings"]["side"] == "1P" and hello["has_gif"] is False
        assert hello["devices"] == [] and hello["bindings"] == {}
        assert hello["counts"] == {t: 0 for t in TARGETS}
        ctx.bus.publish(make_event("key_down", lane="3", dir=None, t=1.0))
        assert ws.receive_json()["lane"] == "3"


def test_patch_settings_broadcasts(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        r = client.patch("/api/settings", json={"side": "2P"})
        assert r.status_code == 200 and r.json()["side"] == "2P"
        ev = ws.receive_json()
        assert ev["type"] == "settings" and ev["settings"]["side"] == "2P"
    assert client.get("/api/settings").json()["side"] == "2P"


def test_patch_settings_invalid_400(client):
    r = client.patch("/api/settings", json={"manual_bpm": -1})
    assert r.status_code == 400 and "error" in r.json()


def test_patch_settings_bad_json_400(client):
    r = client.patch("/api/settings", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 400


def test_bindings_empty(client):
    assert client.get("/api/bindings").json() == {}


def test_gif_upload_rejects_non_gif_and_keeps_old(client):
    good = b"GIF89a" + b"\x00" * 10
    assert client.put("/api/gif", content=good, headers={"content-type": "image/gif"}).status_code == 204
    assert client.put("/api/gif", content=b"\x89PNG....", headers={"content-type": "image/gif"}).status_code == 415
    assert client.put("/api/gif", content=b"", headers={"content-type": "image/gif"}).status_code == 400
    r = client.get("/api/gif")
    assert r.content == good and r.headers["cache-control"] == "no-store"


def test_gif_upload_broadcasts_version(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        client.put("/api/gif", content=b"GIF87a" + b"\x00" * 4, headers={"content-type": "image/gif"})
        ev = ws.receive_json()
        assert ev["type"] == "gif" and ev["version"] > 0
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["has_gif"] is True and hello["gif_version"] == ev["version"]


def test_gif_missing_404(client):
    assert client.get("/api/gif").status_code == 404


def test_gif_too_large_413(client):
    body = b"GIF89a" + b"\x00" * (20 * 1024 * 1024 - 5)
    assert client.put("/api/gif", content=body, headers={"content-type": "image/gif"}).status_code == 413


def test_root_without_build_says_not_built(client):
    r = client.get("/")
    assert r.status_code == 200 and "not built" in r.text


def test_counts_reset_without_input_sends_zeros(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "counts_reset"})
        ev = ws.receive_json()
        assert ev["type"] == "counts" and ev["counts"] == {t: 0 for t in TARGETS}


def test_skin_routes_are_gone(client):
    assert client.get("/api/skin").status_code == 404
    assert client.get("/skin/play/parts/notes/default.png").status_code == 404


class FakeInput:
    def __init__(self):
        self.calls = []

    def devices(self):
        return []

    def counts(self):
        return {t: 0 for t in TARGETS}

    def binding_state(self):
        return {"target": "3", "index": 2, "total": 9}

    def handle_client(self, msg, client=None):
        self.calls.append(("msg", msg["type"], client))

    def client_gone(self, client):
        self.calls.append(("gone", client))


def test_ws_passes_client_id_and_reports_disconnect(ctx):
    from starlette.testclient import TestClient
    from inf_companion.server.app import create_app
    fake = FakeInput()
    ctx.input = fake
    with TestClient(create_app(ctx)) as c:
        with c.websocket_connect("/ws") as ws:
            hello = ws.receive_json()
            assert hello["binding"] == {"target": "3", "index": 2, "total": 9}
            ws.send_json({"type": "bind_start"})
            ws.send_json({"type": "counts_reset"})
        # the socket closed: the server must tell the input service
        import time
        for _ in range(50):
            if any(k == "gone" for k, *_ in fake.calls):
                break
            time.sleep(0.01)
    kinds = [c[0] for c in fake.calls]
    msg_clients = {c[2] for c in fake.calls if c[0] == "msg"}
    gone = [c[1] for c in fake.calls if c[0] == "gone"]
    assert kinds.count("msg") == 2 and len(msg_clients) == 1 and gone == list(msg_clients)


def test_hello_reports_gif_version_and_uploads_always_change_it(ctx, tmp_path):
    from starlette.testclient import TestClient
    from inf_companion.server.app import create_app
    gif = b"GIF89a" + b"\x00" * 10
    with TestClient(create_app(ctx)) as c:
        c.put("/api/gif", content=gif, headers={"content-type": "image/gif"})
        with c.websocket_connect("/ws") as ws:
            v1 = ws.receive_json()["gif_version"]
    assert v1 > 0
    # simulate an app restart: a fresh app over the same data folder
    ctx.gif_version = 0
    with TestClient(create_app(ctx)) as c:
        with c.websocket_connect("/ws") as ws:
            assert ws.receive_json()["gif_version"] == v1   # same file, same version
            c.put("/api/gif", content=gif, headers={"content-type": "image/gif"})
            assert ws.receive_json()["version"] != v1       # a new upload never reuses a version


def test_hello_reports_capture_state(ctx):
    from starlette.testclient import TestClient
    from inf_companion.server.app import create_app
    with TestClient(create_app(ctx)) as c, c.websocket_connect("/ws") as ws:
        h = ws.receive_json()
        assert h["screen"] is None and h["capture_status"] == {"state": "off"}

    class FakeCapture:
        def state(self):
            return {"screen": "result", "capture_status": {"state": "running"}}

    ctx.capture = FakeCapture()
    with TestClient(create_app(ctx)) as c, c.websocket_connect("/ws") as ws:
        h = ws.receive_json()
        assert h["screen"] == "result" and h["capture_status"] == {"state": "running"}


def test_hello_carries_chart(ctx):
    from starlette.testclient import TestClient
    from inf_companion.server.app import create_app
    with TestClient(create_app(ctx)) as c, c.websocket_connect("/ws") as ws:
        h = ws.receive_json()
        assert h["chart"] is None and h["personal_best"] is None

    class FakeCapture:
        def state(self):
            return {"screen": "music_select", "capture_status": {"state": "running"},
                    "chart": {"title": "Mermaid girl"}, "personal_best": {"score": 1437}}

    ctx.capture = FakeCapture()
    with TestClient(create_app(ctx)) as c, c.websocket_connect("/ws") as ws:
        h = ws.receive_json()
        assert h["chart"] == {"title": "Mermaid girl"} and h["personal_best"] == {"score": 1437}


def test_results_become_recent_plays(ctx):
    from starlette.testclient import TestClient
    from inf_companion.server.app import create_app, record_plays
    from inf_companion.storage.db import PlaysRepo, open_db
    ctx.plays = PlaysRepo(open_db(ctx.data_dir / "c.sqlite3"))
    on_message = record_plays(ctx)
    result = {"side": "1P", "playmode": "SP", "title": "Mermaid girl", "difficulty": "HYPER", "level": 8,
              "notes": 856, "cleartype": "CLEAR", "score": 1228,
              "judges": {"pgreat": 485, "great": 258, "good": 100, "bad": 4, "poor": 10}}
    with TestClient(create_app(ctx)) as c, c.websocket_connect("/ws") as ws:
        assert ws.receive_json()["recent_plays"] == []
        on_message({"type": "screen", "screen": "result"})
        on_message({"type": "result", "result": result})
        on_message({"type": "result", "result": result})  # the same result again: not a new play
        e = ws.receive_json()
        assert e["type"] == "recent_plays" and [p["score"] for p in e["plays"]] == [1228]
    with TestClient(create_app(ctx)) as c, c.websocket_connect("/ws") as ws:
        assert [p["title"] for p in ws.receive_json()["recent_plays"]] == ["Mermaid girl"]
