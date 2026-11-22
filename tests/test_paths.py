from inf_companion.cli import parse_args
from inf_companion.paths import resolve_data_dir


def test_arg_wins_over_env(tmp_path):
    p = resolve_data_dir(str(tmp_path / "a"), env={"INF_COMPANION_DATA": str(tmp_path / "b")})
    assert p == (tmp_path / "a").resolve() and p.is_dir()


def test_env_used_when_no_arg(tmp_path):
    assert resolve_data_dir(None, env={"INF_COMPANION_DATA": str(tmp_path / "b")}) == (tmp_path / "b").resolve()


def test_default_is_cwd_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resolve_data_dir(None, env={}) == (tmp_path / "data").resolve()


def test_parse_args_defaults():
    a = parse_args([])
    assert (a.host, a.port, a.data_dir, a.no_input) == ("127.0.0.1", 8765, None, False)
