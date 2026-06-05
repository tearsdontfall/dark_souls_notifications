"""
Build Dark Souls Meetings.app (run from this directory):

    cd macos_app
    pip install py2app
    python setup.py py2app
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from setuptools import setup

APP = [str(ROOT / "src" / "notifications" / "app.py")]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "Dark Souls Meetings",
        "CFBundleDisplayName": "Dark Souls Meetings",
        "CFBundleIdentifier": "com.knolss.dark-souls-meetings",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,
        "NSCalendarsUsageDescription": (
            "Dark Souls Meetings reads your calendars to show meeting reminders."
        ),
    },
    "packages": ["notifications"],
    "includes": [
        "objc",
        "PyObjCTools",
        "EventKit",
        "AppKit",
        "Foundation",
    ],
}

setup(
    name="Dark Souls Meetings",
    version="0.1.0",
    app=APP,
    options={"py2app": OPTIONS},
)
