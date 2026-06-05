from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import AppKit
import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSClosableWindowMask,
    NSTextField,
    NSTitledWindowMask,
    NSView,
    NSWindow,
)
from Foundation import NSMakeRect, NSObject

from notifications.config import CONFIG_DIR, CONFIG_PATH, AppConfig, load_config, save_config
from notifications.logging_config import get_logger
from notifications.sounds import play_notification

logger = get_logger()

WINDOW_WIDTH = 520
WINDOW_HEIGHT = 200
SOUND_EXTENSIONS = ["wav", "mp3", "aiff", "aif", "m4a", "caf", "aac"]


def _show_alert(title: str, message: str) -> None:
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    alert.runModal()


def _load_or_default_config() -> AppConfig:
    if CONFIG_PATH.exists():
        return load_config()
    return AppConfig()


def _display_name(path: str | None) -> str:
    if not path:
        return "None (silent)"
    name = Path(path).expanduser().name
    return name if len(name) <= 48 else name[:45] + "…"


class SoundWindowController(NSObject):
    window = objc.ivar()
    path_label = objc.ivar()
    config = objc.ivar()
    sound_path = objc.ivar()
    on_complete = objc.ivar()
    on_cancel = objc.ivar()

    def initWithOnComplete_onCancel_(self, on_complete, on_cancel):
        self = objc.super(SoundWindowController, self).init()
        if self is None:
            return None
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.config = _load_or_default_config()
        self.sound_path = self.config.sound_path
        return self

    def show(self) -> None:
        self._build_window()
        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def _build_window(self) -> None:
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT),
            NSTitledWindowMask | NSClosableWindowMask,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Notification Sound")
        self.window.setReleasedWhenClosed_(False)
        self.window.center()

        root = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))

        title = NSTextField.alloc().initWithFrame_(NSMakeRect(16, 148, WINDOW_WIDTH - 32, 20))
        title.setStringValue_("Sound played when the summon strip appears:")
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setSelectable_(False)
        root.addSubview_(title)

        self.path_label = NSTextField.alloc().initWithFrame_(NSMakeRect(16, 118, WINDOW_WIDTH - 32, 22))
        self.path_label.setStringValue_(_display_name(self.sound_path))
        self.path_label.setBezeled_(True)
        self.path_label.setDrawsBackground_(True)
        self.path_label.setEditable_(False)
        self.path_label.setSelectable_(True)
        root.addSubview_(self.path_label)

        choose_btn = NSButton.alloc().initWithFrame_(NSMakeRect(16, 72, 130, 32))
        choose_btn.setTitle_("Choose file…")
        choose_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        choose_btn.setTarget_(self)
        choose_btn.setAction_("chooseFile:")
        root.addSubview_(choose_btn)

        clear_btn = NSButton.alloc().initWithFrame_(NSMakeRect(154, 72, 110, 32))
        clear_btn.setTitle_("Disable sound")
        clear_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        clear_btn.setTarget_(self)
        clear_btn.setAction_("clearSound:")
        root.addSubview_(clear_btn)

        test_btn = NSButton.alloc().initWithFrame_(NSMakeRect(272, 72, 110, 32))
        test_btn.setTitle_("Test sound")
        test_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        test_btn.setTarget_(self)
        test_btn.setAction_("testSound:")
        root.addSubview_(test_btn)

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

        self.window.setContentView_(root)

    def _update_path_label(self) -> None:
        self.path_label.setStringValue_(_display_name(self.sound_path))

    def chooseFile_(self, _sender) -> None:
        panel = AppKit.NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setAllowedFileTypes_(SOUND_EXTENSIONS)
        panel.setTitle_("Choose notification sound")

        sounds_dir = CONFIG_DIR / "sounds"
        if sounds_dir.is_dir():
            panel.setDirectoryURL_(AppKit.NSURL.fileURLWithPath_(str(sounds_dir)))

        if panel.runModal() != AppKit.NSFileHandlingPanelOKButton:
            return

        urls = panel.URLs()
        if not urls:
            return

        path = urls[0].path()
        if not path:
            return

        self.sound_path = path
        self._update_path_label()

    def clearSound_(self, _sender) -> None:
        self.sound_path = None
        self._update_path_label()

    def testSound_(self, _sender) -> None:
        if not self.sound_path:
            _show_alert("No Sound", "Choose a sound file first, or sound is disabled.")
            return
        path = Path(self.sound_path).expanduser()
        if not path.is_file():
            _show_alert("File Not Found", f"Sound file not found:\n{path}")
            return
        play_notification(str(path))

    def save_(self, _sender) -> None:
        if self.sound_path:
            path = Path(self.sound_path).expanduser()
            if not path.is_file():
                _show_alert("File Not Found", f"Sound file not found:\n{path}")
                return
            stored_path = str(path)
        else:
            stored_path = None

        self.config.sound_path = stored_path
        if not self.config.calendar_ids and not CONFIG_PATH.exists():
            _show_alert(
                "Calendars Required",
                "Select calendars first (menu → Select calendars…). "
                "Sound setting was not saved.",
            )
            if self.on_cancel:
                self.on_cancel()
            self.window.orderOut_(None)
            return

        save_config(self.config)
        logger.info("Sound path saved: %s", stored_path or "disabled")
        self.window.orderOut_(None)
        if self.on_complete:
            self.on_complete()

    def cancel_(self, _sender) -> None:
        self.window.orderOut_(None)
        if self.on_cancel:
            self.on_cancel()


_active_controller: SoundWindowController | None = None


def show_sound_window(
    on_complete: Callable[[], None] | None = None,
    on_cancel: Callable[[], None] | None = None,
) -> None:
    global _active_controller
    _active_controller = SoundWindowController.alloc().initWithOnComplete_onCancel_(
        on_complete,
        on_cancel,
    )
    _active_controller.show()
