import os

import pytest

from inf_companion.server.skin import list_skin, resolve_skin_file


def test_resolves_png_inside(skin):
    assert resolve_skin_file(skin, "play/parts/notes/default.png") == (skin / "play/parts/notes/default.png").resolve()


@pytest.mark.parametrize(
    "rel", ["../secret.png", "/etc/passwd", "play/parts/notes/readme.lua", "play/parts/notes/missing.png", "play/parts/notes"]
)
def test_skin_route_blocks_escape(skin, rel):
    (skin.parent / "secret.png").write_bytes(b"x")
    assert resolve_skin_file(skin, rel) is None


def test_symlink_out_of_skin_blocked(skin, tmp_path):
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    os.symlink(outside, skin / "evil.png")
    assert resolve_skin_file(skin, "evil.png") is None


def test_list_skin(skin, tmp_path):
    assert list_skin(skin) == {"available": True, "notes": ["default"]}
    assert list_skin(tmp_path / "nope") == {"available": False, "notes": []}


def test_skin_http_404_and_200(client_with_skin):
    assert client_with_skin.get("/skin/../secret.png").status_code == 404
    assert client_with_skin.get("/skin/play/parts/notes/readme.lua").status_code == 404
    r = client_with_skin.get("/skin/play/parts/notes/default.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert client_with_skin.get("/api/skin").json()["available"] is True
