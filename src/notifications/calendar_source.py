from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from EventKit import (
    EKAuthorizationStatusAuthorized,
    EKEntityTypeEvent,
    EKEvent,
    EKEventStore,
    EKParticipantStatusDeclined,
)
from Foundation import NSDate

from notifications.config import AppConfig


@dataclass(frozen=True)
class CalendarInfo:
    calendar_id: str
    title: str
    source_title: str


@dataclass(frozen=True)
class MeetingEvent:
    event_id: str
    title: str
    start_timestamp: float
    dedup_key: str

    @property
    def start_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.start_timestamp)


def _nsdate_from_datetime(dt: datetime) -> NSDate:
    return NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())


def _datetime_from_nsdate(ns_date) -> datetime:
    return datetime.fromtimestamp(ns_date.timeIntervalSince1970())


def create_event_store() -> EKEventStore:
    return EKEventStore.alloc().init()


def request_calendar_access(store: EKEventStore) -> bool:
    status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
    if status == EKAuthorizationStatusAuthorized:
        return True

    granted_holder: list[bool] = []

    def completion(granted, error):
        granted_holder.append(bool(granted))

    store.requestAccessToEntityType_completion_(EKEntityTypeEvent, completion)

    from Foundation import NSDate, NSDefaultRunLoopMode, NSRunLoop

    run_loop = NSRunLoop.currentRunLoop()
    deadline = time.time() + 120
    while not granted_holder and time.time() < deadline:
        run_loop.runMode_beforeDate_(
            NSDefaultRunLoopMode,
            NSDate.dateWithTimeIntervalSinceNow_(0.1),
        )

    if granted_holder:
        return granted_holder[0]

    return EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent) == (
        EKAuthorizationStatusAuthorized
    )


def list_calendars(store: EKEventStore) -> list[CalendarInfo]:
    calendars = store.calendarsForEntityType_(EKEntityTypeEvent) or []
    result: list[CalendarInfo] = []
    for cal in calendars:
        source = cal.source()
        source_title = source.title() if source else "Unknown"
        result.append(
            CalendarInfo(
                calendar_id=cal.calendarIdentifier(),
                title=cal.title() or "Untitled",
                source_title=source_title,
            )
        )
    return sorted(result, key=lambda c: (c.source_title.lower(), c.title.lower()))


def _is_all_day(event: EKEvent) -> bool:
    return bool(event.isAllDay())


def _is_declined(event: EKEvent) -> bool:
    for participant in event.attendees() or []:
        if participant.isCurrentUser():
            status = participant.participantStatus()
            if status == EKParticipantStatusDeclined:
                return True
    return False


def _event_to_meeting(event: EKEvent) -> MeetingEvent | None:
    if _is_all_day(event):
        return None
    if _is_declined(event):
        return None

    title = (event.title() or "").strip()
    if not title:
        return None

    start = event.startDate()
    if start is None:
        return None

    start_ts = start.timeIntervalSince1970()
    event_id = event.eventIdentifier() or f"{title}:{start_ts}"
    dedup_key = f"{event_id}:{int(start_ts)}"
    return MeetingEvent(
        event_id=event_id,
        title=title,
        start_timestamp=start_ts,
        dedup_key=dedup_key,
    )


def get_selected_calendars(store: EKEventStore, calendar_ids: list[str]):
    all_cals = store.calendarsForEntityType_(EKEntityTypeEvent) or []
    id_set = set(calendar_ids)
    return [c for c in all_cals if c.calendarIdentifier() in id_set]


def fetch_upcoming_meetings(
    store: EKEventStore,
    config: AppConfig,
    horizon_minutes: int = 5,
) -> list[MeetingEvent]:
    calendars = get_selected_calendars(store, config.calendar_ids)
    if not calendars:
        return []

    now = datetime.now()
    end = now + timedelta(minutes=horizon_minutes)
    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(
        _nsdate_from_datetime(now),
        _nsdate_from_datetime(end),
        calendars,
    )
    if predicate is None:
        return []

    raw_events = store.eventsMatchingPredicate_(predicate) or []
    meetings: list[MeetingEvent] = []
    for event in raw_events:
        meeting = _event_to_meeting(event)
        if meeting is not None:
            meetings.append(meeting)

    meetings.sort(key=lambda m: m.start_timestamp)
    return meetings


def seconds_until_start(meeting: MeetingEvent) -> float:
    return meeting.start_timestamp - time.time()
