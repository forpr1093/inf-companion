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
        assert ev["type"] == "gif" and ev["version"] == 1
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["has_gif"] is True


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
