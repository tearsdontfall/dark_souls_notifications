from __future__ import annotations

from datetime import datetime

import AppKit
from AppKit import (
    NSBackingStoreBuffered,
    NSBorderlessWindowMask,
    NSColor,
    NSFont,
    NSScreen,
    NSTextField,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
)
from Foundation import NSMakeRect, NSShadow
from PyObjCTools import AppHelper

from notifications.config import AppConfig
from notifications.sounds import play_notification

STRIP_HEIGHT = 88
TAGLINE = "ПРИБЛИЖАЕТСЯ ИСПЫТАНИЕ"

# Keep windows alive until dismiss; prevents GC + timer segfaults in PyObjC.
_active_windows: list = []


def _crimson_color() -> NSColor:
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(0.77, 0.12, 0.23, 1.0)


def _dark_background() -> NSColor:
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(0.04, 0.02, 0.02, 0.94)


def _text_shadow() -> NSShadow:
    shadow = NSShadow.alloc().init()
    shadow.setShadowOffset_((0, -1))
    shadow.setShadowBlurRadius_(6)
    shadow.setShadowColor_(
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.5, 0, 0, 0.8)
    )
    return shadow


def _make_label(
    frame,
    text: str,
    font_size: float,
    bold: bool = False,
) -> NSTextField:
    label = NSTextField.alloc().initWithFrame_(frame)
    label.setStringValue_(text)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setTextColor_(_crimson_color())
    label.setAlignment_(AppKit.NSTextAlignmentCenter)
    font = NSFont.fontWithName_size_("Palatino-Bold" if bold else "Palatino", font_size)
    if font is None:
        font = NSFont.boldSystemFontOfSize_(font_size) if bold else NSFont.systemFontOfSize_(
            font_size
        )
    label.setFont_(font)
    label.setShadow_(_text_shadow())
    return label


def _strip_origin_y(screen_frame) -> float:
    """Vertical center of the main screen."""
    return screen_frame.origin.y + (screen_frame.size.height - STRIP_HEIGHT) / 2


def show_meeting_overlay(
    title: str,
    start_time: datetime,
    config: AppConfig,
) -> None:
    """Show full-width strip centered on screen. Must run on main thread."""
    play_notification(config.sound_path)

    screen = NSScreen.mainScreen()
    if screen is None:
        return

    frame = screen.frame()
    window_width = frame.size.width
    window_x = frame.origin.x
    window_y = _strip_origin_y(frame)

    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(window_x, window_y, window_width, STRIP_HEIGHT),
        NSBorderlessWindowMask,
        NSBackingStoreBuffered,
        False,
    )
    window.setReleasedWhenClosed_(False)
    window.setLevel_(AppKit.NSStatusWindowLevel + 1)
    window.setOpaque_(True)
    window.setBackgroundColor_(_dark_background())
    window.setHasShadow_(True)
    window.setIgnoresMouseEvents_(True)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorStationary
        | NSWindowCollectionBehaviorIgnoresCycle
    )

    content = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, window_width, STRIP_HEIGHT))
    window.setContentView_(content)

    time_str = start_time.strftime("%H:%M")
    tagline = _make_label(NSMakeRect(0, STRIP_HEIGHT - 34, window_width, 22), TAGLINE, 13, True)
    meeting = _make_label(
        NSMakeRect(40, 28, window_width - 80, 28),
        title,
        18,
        True,
    )
    subtitle = _make_label(
        NSMakeRect(0, 8, window_width, 18),
        f"Созвон начнётся в {time_str}",
        12,
    )

    content.addSubview_(tagline)
    content.addSubview_(meeting)
    content.addSubview_(subtitle)

    _active_windows.append(window)
    window.orderFrontRegardless()

    duration = config.overlay_duration_seconds

    def dismiss():
        try:
            window.orderOut_(None)
        finally:
            if window in _active_windows:
                _active_windows.remove(window)

    AppHelper.callLater(duration, dismiss)


def show_meeting_overlay_safe(
    title: str,
    start_time: datetime,
    config: AppConfig,
) -> None:
    """Schedule overlay on AppKit main thread."""
    AppHelper.callAfter(lambda: show_meeting_overlay(title, start_time, config))
