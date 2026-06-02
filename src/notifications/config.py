from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "dark-souls-meetings"
CONFIG_PATH = CONFIG_DIR / "config.json"
CACHE_DIR = Path.home() / ".cache" / "dark-souls-meetings"
NOTIFIED_CACHE_PATH = CACHE_DIR / "notified.json"


@dataclass
class AppConfig:
    calendar_ids: list[str] = field(default_factory=list)
    minutes_before: int = 2
    poll_interval_seconds: int = 30
    overlay_duration_seconds: int = 5
    sound_path: str | None = None

    @property
    def notify_seconds(self) -> int:
        return self.minutes_before * 60

    @property
    def notify_window_low(self) -> int:
        """Lower bound (seconds before start) for trigger window."""
        return self.notify_seconds - 15

    @property
    def notify_window_high(self) -> int:
        """Upper bound (seconds before start) for trigger window."""
        return self.notify_seconds + 15


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found at {CONFIG_PATH}. Run: python -m notifications setup"
        )
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return AppConfig(
        calendar_ids=data.get("calendar_ids", []),
        minutes_before=data.get("minutes_before", 2),
        poll_interval_seconds=data.get("poll_interval_seconds", 30),
        overlay_duration_seconds=data.get("overlay_duration_seconds", 5),
        sound_path=data.get("sound_path"),
    )


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "calendar_ids": config.calendar_ids,
        "minutes_before": config.minutes_before,
        "poll_interval_seconds": config.poll_interval_seconds,
        "overlay_duration_seconds": config.overlay_duration_seconds,
        "sound_path": config.sound_path,
    }
    CONFIG_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
