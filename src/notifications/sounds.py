from __future__ import annotations

import subprocess
from pathlib import Path


def play_notification(sound_path: str | None) -> None:
    """Play notification sound via afplay. No-op when sound_path is None."""
    if not sound_path:
        return
    path = Path(sound_path).expanduser()
    if not path.is_file():
        try:
            from notifications.logging_config import get_logger

            get_logger().warning("Sound file not found: %s", path)
        except Exception:
            pass
        return
    # TODO: richer audio (volume, multiple cues)
    subprocess.Popen(
        ["afplay", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
