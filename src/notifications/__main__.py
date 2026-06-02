from __future__ import annotations

import sys


def run_setup() -> None:
    from notifications.setup import run_setup_interactive

    raise SystemExit(run_setup_interactive())


def run_watch() -> None:
    from notifications.watcher import run_watch as _run_watch

    raise SystemExit(_run_watch())


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m notifications {setup|watch}", file=sys.stderr)
        raise SystemExit(1)

    command = sys.argv[1].lower()
    if command == "setup":
        run_setup()
    elif command == "watch":
        run_watch()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Usage: python -m notifications {setup|watch}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
