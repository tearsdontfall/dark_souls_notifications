"""
Convenience wrapper — builds from macos_app/ to avoid py2app + pyproject.toml conflict.

    pip install -e ".[build]"
    python setup_app.py py2app
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MACOS_APP_DIR = Path(__file__).resolve().parent / "macos_app"


def main() -> None:
    cmd = [sys.executable, "setup.py", *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd, cwd=MACOS_APP_DIR))


if __name__ == "__main__":
    main()
