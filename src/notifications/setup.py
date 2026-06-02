from __future__ import annotations

import sys

from notifications.calendar_source import (
    create_event_store,
    list_calendars,
    request_calendar_access,
)
from notifications.config import AppConfig, save_config


def run_setup_interactive() -> int:
    store = create_event_store()
    print("Requesting Calendar access…")
    print("If prompted, allow access in System Settings → Privacy & Security → Calendar.")

    if not request_calendar_access(store):
        print(
            "Calendar access was not granted. Enable it for Terminal/Python, then run setup again.",
            file=sys.stderr,
        )
        return 1

    calendars = list_calendars(store)
    if not calendars:
        print("No calendars found.", file=sys.stderr)
        return 1

    print("\nAvailable calendars:\n")
    for idx, cal in enumerate(calendars, start=1):
        print(f"  {idx:2}. {cal.title}  [{cal.source_title}]")

    print(
        "\nEnter calendar numbers to watch (comma-separated, e.g. 1,3)"
        "\nor 'all' for every calendar:"
    )
    choice = input("> ").strip().lower()

    if choice == "all":
        selected_ids = [c.calendar_id for c in calendars]
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
        except ValueError:
            print("Invalid input.", file=sys.stderr)
            return 1

        selected_ids = []
        for i in indices:
            if i < 1 or i > len(calendars):
                print(f"Invalid number: {i}", file=sys.stderr)
                return 1
            selected_ids.append(calendars[i - 1].calendar_id)

    if not selected_ids:
        print("No calendars selected.", file=sys.stderr)
        return 1

    config = AppConfig(calendar_ids=selected_ids)
    save_config(config)

    names = [c.title for c in calendars if c.calendar_id in selected_ids]
    print(f"\nSaved {len(selected_ids)} calendar(s) to config:")
    for name in names:
        print(f"  • {name}")
    print("\nStart the watcher: python -m notifications watch")
    return 0
