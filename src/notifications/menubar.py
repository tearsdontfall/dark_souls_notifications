from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import AppKit
import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

from notifications.config import CONFIG_DIR, CONFIG_PATH
from notifications.engine import WatcherEngine
from notifications.logging_config import LOG_PATH, setup_logging
from notifications.overlay import show_meeting_overlay_safe
from notifications.setup_gui import show_setup_window

logger = setup_logging()


class MenuBarAppDelegate(NSObject):
    engine = objc.ivar()
    status_item = objc.ivar()
    menu = objc.ivar()
    status_menu_item = objc.ivar()
    next_menu_item = objc.ivar()
    pause_menu_item = objc.ivar()

    def init(self):
        self = objc.super(MenuBarAppDelegate, self).init()
        if self is None:
            return None
        self.engine = WatcherEngine(on_poll=self._on_engine_poll)
        return self

    def applicationDidFinishLaunching_(self, notification) -> None:
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = self.status_item.button()
        if button is not None:
            button.setTitle_("⚔")

        self.menu = NSMenu.alloc().init()
        self.status_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "○ Starting…", None, ""
        )
        self.status_menu_item.setEnabled_(False)
        self.menu.addItem_(self.status_menu_item)

        self.next_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Next: —", None, ""
        )
        self.next_menu_item.setEnabled_(False)
        self.menu.addItem_(self.next_menu_item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        self.pause_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Pause", "togglePause:", ""
        )
        self.menu.addItem_(self.pause_menu_item)

        test_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Test notification", "testNotification:", ""
        )
        self.menu.addItem_(test_item)

        calendars_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Select calendars…", "selectCalendars:", ""
        )
        self.menu.addItem_(calendars_item)

        config_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open config folder", "openConfigFolder:", ""
        )
        self.menu.addItem_(config_item)

        log_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show log in Finder", "showLog:", ""
        )
        self.menu.addItem_(log_item)

        self.menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "quitApp:", "q")
        quit_item.setTarget_(self)
        self.menu.addItem_(quit_item)

        self.status_item.setMenu_(self.menu)

        if CONFIG_PATH.exists():
            self._start_engine()
        else:
            self._update_menu_labels()
            show_setup_window(
                on_complete=self._on_setup_complete,
                on_cancel=self._on_setup_cancelled,
            )

    def applicationWillTerminate_(self, notification) -> None:
        self.engine.stop()

    def _on_setup_complete(self) -> None:
        self._start_engine()

    def _on_setup_cancelled(self) -> None:
        self._update_menu_labels()
        if not CONFIG_PATH.exists():
            logger.warning("Setup cancelled without config; app stays idle until calendars are selected")

    def _start_engine(self) -> None:
        if self.engine.start():
            self._update_menu_labels()
        else:
            self._update_menu_labels()
            self._show_error(self.engine.last_error or "Failed to start watcher")

    def _on_engine_poll(self, engine: WatcherEngine) -> None:
        AppHelper.callAfter(lambda: self._update_menu_labels())

    def _update_menu_labels(self) -> None:
        engine = self.engine
        if engine.is_watching:
            self.status_menu_item.setTitle_("● Watching")
            self.pause_menu_item.setTitle_("Pause")
        elif engine.paused:
            self.status_menu_item.setTitle_("○ Paused")
            self.pause_menu_item.setTitle_("Resume")
        elif engine.last_error:
            self.status_menu_item.setTitle_("○ Error")
            self.pause_menu_item.setTitle_("Resume")
        else:
            self.status_menu_item.setTitle_("○ Idle")
            self.pause_menu_item.setTitle_("Resume")

        next_meeting = engine.next_meeting
        if next_meeting is not None:
            title = next_meeting.title
            if len(title) > 36:
                title = title[:33] + "…"
            time_str = next_meeting.start_datetime.strftime("%H:%M")
            self.next_menu_item.setTitle_(f"Next: {title} at {time_str}")
        else:
            self.next_menu_item.setTitle_("Next: —")

    def togglePause_(self, _sender) -> None:
        if self.engine.is_watching:
            self.engine.pause()
        else:
            if not CONFIG_PATH.exists():
                show_setup_window(on_complete=self._on_setup_complete)
                return
            self.engine.resume()
        self._update_menu_labels()

    def testNotification_(self, _sender) -> None:
        if self.engine.config is None:
            if not self.engine.reload_config():
                self._show_error("Configure calendars first.")
                return
        config = self.engine.config
        show_meeting_overlay_safe(
            "Test Meeting",
            datetime.now() + timedelta(minutes=2),
            config,
        )
        logger.info("Test notification triggered from menu")

    def selectCalendars_(self, _sender) -> None:
        was_running = self.engine.is_watching
        if was_running:
            self.engine.pause()

        def on_complete():
            self.engine.stop()
            self.engine.start()
            self._update_menu_labels()

        def on_cancel():
            if was_running:
                self.engine.resume()
            self._update_menu_labels()

        show_setup_window(on_complete=on_complete, on_cancel=on_cancel)

    def openConfigFolder_(self, _sender) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["open", str(CONFIG_DIR)])

    def quitApp_(self, _sender) -> None:
        self.engine.stop()
        NSApplication.sharedApplication().terminate_(None)

    def showLog_(self, _sender) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_PATH.exists():
            LOG_PATH.touch()
        subprocess.Popen(["open", "-R", str(LOG_PATH)])

    def _show_error(self, message: str) -> None:
        logger.error(message)
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Dark Souls Meetings")
        alert.setInformativeText_(message)
        alert.runModal()


_delegate: MenuBarAppDelegate | None = None


def run_menubar_app() -> int:
    global _delegate
    app = NSApplication.sharedApplication()
    _delegate = MenuBarAppDelegate.alloc().init()
    app.setDelegate_(_delegate)
    AppHelper.runEventLoop()
    return 0
