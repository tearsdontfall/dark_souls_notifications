from __future__ import annotations

from collections.abc import Callable

import AppKit
import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSClosableWindowMask,
    NSScrollView,
    NSTitledWindowMask,
    NSView,
    NSWindow,
)
from Foundation import NSMakeRect, NSObject

from notifications.calendar_source import create_event_store, list_calendars, request_calendar_access
from notifications.config import AppConfig, save_config
from notifications.logging_config import get_logger

logger = get_logger()

ROW_HEIGHT = 28
WINDOW_WIDTH = 520
WINDOW_HEIGHT = 420


def _show_alert(title: str, message: str) -> None:
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    alert.runModal()


class SetupWindowController(NSObject):
    window = objc.ivar()
    scroll_view = objc.ivar()
    content_view = objc.ivar()
    checkboxes = objc.ivar()
    calendars = objc.ivar()
    on_complete = objc.ivar()
    on_cancel = objc.ivar()

    def initWithOnComplete_onCancel_(self, on_complete, on_cancel):
        self = objc.super(SetupWindowController, self).init()
        if self is None:
            return None
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.checkboxes = []
        self.calendars = []
        return self

    def show(self) -> None:
        store = create_event_store()
        if not request_calendar_access(store):
            _show_alert(
                "Calendar Access Required",
                "Enable calendar access for this app in System Settings → "
                "Privacy & Security → Calendar, then try again.",
            )
            if self.on_cancel:
                self.on_cancel()
            return

        self.calendars = list_calendars(store)
        if not self.calendars:
            _show_alert("No Calendars", "No calendars were found on this Mac.")
            if self.on_cancel:
                self.on_cancel()
            return

        self._build_window()
        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def _build_window(self) -> None:
        content_height = max(len(self.calendars) * ROW_HEIGHT + 16, 120)

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT),
            NSTitledWindowMask | NSClosableWindowMask,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Select Calendars")
        self.window.setReleasedWhenClosed_(False)
        self.window.center()

        root = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

        self.scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(16, 64, WINDOW_WIDTH - 32, 300))
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setAutohidesScrollers_(True)
        self.scroll_view.setBorderType_(AppKit.NSBezelBorder)

        self.content_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, WINDOW_WIDTH - 48, content_height))
        self.checkboxes = []

        for index, cal in enumerate(self.calendars):
            y = content_height - (index + 1) * ROW_HEIGHT
            checkbox = NSButton.alloc().initWithFrame_(
                NSMakeRect(8, y, WINDOW_WIDTH - 64, ROW_HEIGHT - 4)
            )
            checkbox.setButtonType_(AppKit.NSSwitchButton)
            checkbox.setTitle_(f"{cal.title}  [{cal.source_title}]")
            checkbox.setState_(AppKit.NSOnState)
            self.content_view.addSubview_(checkbox)
            self.checkboxes.append(checkbox)

        self.scroll_view.setDocumentView_(self.content_view)
        root.addSubview_(self.scroll_view)

        save_btn = NSButton.alloc().initWithFrame_(NSMakeRect(WINDOW_WIDTH - 196, 16, 84, 32))
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        save_btn.setTarget_(self)
        save_btn.setAction_("save:")
        root.addSubview_(save_btn)

        cancel_btn = NSButton.alloc().initWithFrame_(NSMakeRect(WINDOW_WIDTH - 104, 16, 84, 32))
        cancel_btn.setTitle_("Cancel")
        cancel_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_("cancel:")
        root.addSubview_(cancel_btn)

        select_all_btn = NSButton.alloc().initWithFrame_(NSMakeRect(16, 16, 100, 32))
        select_all_btn.setTitle_("Select All")
        select_all_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        select_all_btn.setTarget_(self)
        select_all_btn.setAction_("selectAll:")
        root.addSubview_(select_all_btn)

        self.window.setContentView_(root)

    def selectAll_(self, _sender) -> None:
        for checkbox in self.checkboxes:
            checkbox.setState_(AppKit.NSOnState)

    def save_(self, _sender) -> None:
        selected_ids: list[str] = []
        for checkbox, cal in zip(self.checkboxes, self.calendars, strict=True):
            if checkbox.state() == AppKit.NSOnState:
                selected_ids.append(cal.calendar_id)

        if not selected_ids:
            _show_alert("Nothing Selected", "Select at least one calendar.")
            return

        config = AppConfig(calendar_ids=selected_ids)
        save_config(config)
        logger.info("Saved %s calendar(s) from setup GUI", len(selected_ids))
        self.window.orderOut_(None)
        if self.on_complete:
            self.on_complete()

    def cancel_(self, _sender) -> None:
        self.window.orderOut_(None)
        if self.on_cancel:
            self.on_cancel()


_active_controller: SetupWindowController | None = None


def show_setup_window(
    on_complete: Callable[[], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
) -> None:
    global _active_controller
    _active_controller = SetupWindowController.alloc().initWithOnComplete_onCancel_(
        on_complete,
        on_cancel,
    )
    _active_controller.show()
