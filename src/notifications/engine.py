from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PyObjCTools import AppHelper

from notifications.calendar_source import (
    MeetingEvent,
    create_event_store,
    fetch_upcoming_meetings,
    request_calendar_access,
    seconds_until_start,
)
from notifications.config import (
    CACHE_DIR,
    CONFIG_PATH,
    NOTIFIED_CACHE_PATH,
    AppConfig,
    load_config,
)
from notifications.logging_config import get_logger
from notifications.overlay import show_meeting_overlay_safe

logger = get_logger()

OnSummonCallback = Callable[[str, MeetingEvent], None]
OnPollCallback = Callable[["WatcherEngine"], None]


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


class WatcherEngine:
    def __init__(
        self,
        on_summon: OnSummonCallback | None = None,
        on_poll: OnPollCallback | None = None,
    ) -> None:
        self.on_summon = on_summon
        self.on_poll = on_poll
        self.running = False
        self.paused = False
        self.store: Any = None
        self.config: AppConfig | None = None
        self.notified: set[str] = set()
        self.last_error: str | None = None
        self.next_meeting: MeetingEvent | None = None
        self._poll_scheduled = False

    @property
    def is_watching(self) -> bool:
        return self.running and not self.paused and self.config is not None

    def reload_config(self) -> bool:
        try:
            self.config = load_config()
            self.last_error = None
            return bool(self.config.calendar_ids)
        except FileNotFoundError as exc:
            self.config = None
            self.last_error = str(exc)
            return False

    def start(self) -> bool:
        if self.running:
            return self.is_watching

        if not CONFIG_PATH.exists():
            self.last_error = "Config not found. Select calendars first."
            logger.warning(self.last_error)
            return False

        if not self.reload_config():
            self.last_error = "No calendars configured."
            logger.warning(self.last_error)
            return False

        self.store = create_event_store()
        if not request_calendar_access(self.store):
            self.last_error = "Calendar access not granted."
            logger.error(self.last_error)
            return False

        self.notified = load_notified_keys()
        self.running = True
        self.paused = False
        self._schedule_poll(0)
        logger.info(
            "Watcher started (notify %s min before, poll every %ss)",
            self.config.minutes_before,
            self.config.poll_interval_seconds,
        )
        return True

    def stop(self) -> None:
        self.running = False
        self.paused = False
        self._poll_scheduled = False
        logger.info("Watcher stopped")

    def pause(self) -> None:
        self.paused = True
        logger.info("Watcher paused")

    def resume(self) -> None:
        if not self.running:
            self.start()
            return
        self.paused = False
        logger.info("Watcher resumed")

    def get_next_meeting(self) -> MeetingEvent | None:
        if self.store is None or self.config is None:
            return None
        meetings = fetch_upcoming_meetings(self.store, self.config, horizon_minutes=120)
        return meetings[0] if meetings else None

    def poll_once(self) -> None:
        if not self.running or self.paused or self.config is None or self.store is None:
            return

        try:
            self.next_meeting = self.get_next_meeting()
            meetings = fetch_upcoming_meetings(self.store, self.config)
            low = self.config.notify_window_low
            high = self.config.notify_window_high

            for meeting in meetings:
                delta = seconds_until_start(meeting)
                if not (low <= delta <= high):
                    continue
                if meeting.dedup_key in self.notified:
                    continue

                self.notified.add(meeting.dedup_key)
                save_notified_keys(self.notified)
                show_meeting_overlay_safe(
                    meeting.title,
                    meeting.start_datetime,
                    self.config,
                )
                logger.info(
                    "Summoned: %s at %s",
                    meeting.title,
                    meeting.start_datetime.strftime("%H:%M"),
                )
                if self.on_summon:
                    self.on_summon(meeting.title, meeting)
                break

            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Poll error: %s", exc)

        if self.on_poll:
            self.on_poll(self)

    def _schedule_poll(self, delay: float) -> None:
        if not self.running:
            return

        def tick():
            self._poll_scheduled = False
            if not self.running:
                return
            self.poll_once()
            if self.running:
                interval = self.config.poll_interval_seconds if self.config else 30
                self._schedule_poll(interval)

        self._poll_scheduled = True
        AppHelper.callLater(delay, tick)
