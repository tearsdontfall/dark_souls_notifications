from __future__ import annotations

import json
import sys

from AppKit import NSApplication
from PyObjCTools import AppHelper

from notifications.calendar_source import (
    create_event_store,
    fetch_upcoming_meetings,
    request_calendar_access,
    seconds_until_start,
)
from notifications.config import CACHE_DIR, NOTIFIED_CACHE_PATH, AppConfig, load_config
from notifications.overlay import show_meeting_overlay_safe


def load_notified_keys() -> set[str]:
    if not NOTIFIED_CACHE_PATH.exists():
        return set()
    try:
        data = json.loads(NOTIFIED_CACHE_PATH.read_text(encoding="utf-8"))
        return set(data.get("keys", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_notified_keys(keys: set[str]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"keys": sorted(keys)}
    NOTIFIED_CACHE_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _poll_once(store, config: AppConfig, notified: set[str]) -> None:
    meetings = fetch_upcoming_meetings(store, config)
    low = config.notify_window_low
    high = config.notify_window_high

    for meeting in meetings:
        delta = seconds_until_start(meeting)
        if not (low <= delta <= high):
            continue
        if meeting.dedup_key in notified:
            continue

        notified.add(meeting.dedup_key)
        save_notified_keys(notified)
        show_meeting_overlay_safe(
            meeting.title,
            meeting.start_datetime,
            config,
        )
        print(f"Summoned: {meeting.title} at {meeting.start_datetime:%H:%M}")
        break


def _schedule_poll(store, config: AppConfig, notified: set[str]) -> None:
    try:
        _poll_once(store, config, notified)
    except Exception as exc:
        print(f"Poll error: {exc}", file=sys.stderr)
    AppHelper.callLater(config.poll_interval_seconds, lambda: _schedule_poll(store, config, notified))


def run_watch() -> int:
    try:
        config = load_config()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not config.calendar_ids:
        print("No calendars configured. Run: python -m notifications setup", file=sys.stderr)
        return 1

    store = create_event_store()
    if not request_calendar_access(store):
        print("Calendar access not granted.", file=sys.stderr)
        return 1

    notified = load_notified_keys()
    print(
        f"Watcher started (notify {config.minutes_before} min before, "
        f"poll every {config.poll_interval_seconds}s). Ctrl+C to stop."
    )

    NSApplication.sharedApplication()
    _schedule_poll(store, config, notified)
    AppHelper.runEventLoop()
    return 0
