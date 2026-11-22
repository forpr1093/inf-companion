"""Command-line entry point: `inf-companion`."""

import argparse

from inf_companion.paths import resolve_data_dir


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="inf-companion", description="Companion app for IIDX INFINITAS")
    p.add_argument("--host", default="127.0.0.1", help="address to listen on (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="port to listen on (default 8765)")
    p.add_argument("--data-dir", default=None, help="data folder (default: $INF_COMPANION_DATA or ./data)")
    p.add_argument("--no-input", action="store_true", help="don't read the controller (no SDL)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = resolve_data_dir(args.data_dir)
    print(data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
