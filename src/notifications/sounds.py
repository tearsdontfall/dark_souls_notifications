from __future__ import annotations

import subprocess
from pathlib import Path


def play_notification(sound_path: str | None) -> None:
    """Play notification sound via afplay. No-op when sound_path is None."""
    if not sound_path:
        return
    path = Path(sound_path).expanduser()
    if not path.is_file():
        import sys

        print(f"Sound file not found: {path}", file=sys.stderr)
        return
    # TODO: richer audio (volume, multiple cues)
    subprocess.Popen(
        ["afplay", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
