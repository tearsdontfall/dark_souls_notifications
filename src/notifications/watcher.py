from __future__ import annotations

import sys

from AppKit import NSApplication
from PyObjCTools import AppHelper

from notifications.engine import WatcherEngine
from notifications.logging_config import setup_logging


def run_watch() -> int:
    setup_logging()
    engine = WatcherEngine(
        on_summon=lambda title, _meeting: print(f"Summoned: {title}"),
    )

    if not engine.start():
        print(engine.last_error or "Failed to start watcher.", file=sys.stderr)
        return 1

    print(
        f"Watcher started (notify {engine.config.minutes_before} min before, "
        f"poll every {engine.config.poll_interval_seconds}s). Ctrl+C to stop."
    )

    NSApplication.sharedApplication()
    AppHelper.runEventLoop()
    return 0
