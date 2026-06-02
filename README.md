# Dark Souls Meeting Notifications

Full-width overlay strip **2 minutes before** calendar meetings, Dark Souls style. Reads **Apple Calendar** via EventKit (including calendars synced from corporate Outlook). **VPN is not required** for the watcher — only Calendar sync on your Mac matters.

## Requirements

- macOS with Apple Calendar
- Python 3.11+
- Calendar permission for Terminal (or your Python app) in **System Settings → Privacy & Security → Calendar**

Screen Recording and Accessibility are **not** required for the overlay.

## Install

```bash
cd /Users/knolss/notifications
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## First run — pick calendars

```bash
python -m notifications setup
```

Choose calendar numbers (comma-separated) or `all`. Config is saved to:

`~/.config/dark-souls-meetings/config.json`

## Run watcher

```bash
python -m notifications watch
```

Or use entry points after install:

```bash
notifications-setup
notifications-watch
```

The watcher polls every 30 seconds and shows a centered full-width strip when a meeting starts in **105–135 seconds** (2 minutes ±15 s).

## Test

1. Create a test event in Calendar starting **3–4 minutes** from now.
2. Run `python -m notifications watch`.
3. About 2 minutes before start you should see **YOU HAVE BEEN SUMMONED** with the event title.

Restarting the watcher should **not** show the same event again (dedup cache at `~/.cache/dark-souls-meetings/notified.json`).

## Config

See [`config.example.json`](config.example.json). Editable fields in `~/.config/dark-souls-meetings/config.json`:

| Field | Default | Description |
|-------|---------|-------------|
| `calendar_ids` | from setup | EventKit calendar identifiers |
| `minutes_before` | 2 | Target minutes before start |
| `poll_interval_seconds` | 30 | Poll interval |
| `overlay_duration_seconds` | 5 | How long the strip stays visible |
| `sound_path` | `null` | Absolute or `~` path to a sound file (see below) |

## Custom sound

1. Put any file **`afplay`** can play (`.wav`, `.mp3`, `.aiff`, `.m4a`, …) anywhere on disk, for example:

   ```text
   ~/.config/dark-souls-meetings/sounds/summon.wav
   ```

2. In `~/.config/dark-souls-meetings/config.json` set **`sound_path`** to the full path:

   ```json
   {
     "sound_path": "/Users/you/.config/dark-souls-meetings/sounds/summon.wav"
   }
   ```

   Tilde works too: `"sound_path": "~/.config/dark-souls-meetings/sounds/summon.mp3"`

3. Restart the watcher. The sound plays when the strip appears. If the path is wrong, the watcher logs `Sound file not found: ...` to stderr and continues without audio.

To disable sound again, set `"sound_path": null`.

## Optional: run at login

Copy and edit [`scripts/com.knolss.meetings-watcher.plist`](scripts/com.knolss.meetings-watcher.plist) with your user and venv paths, then:

```bash
cp scripts/com.knolss.meetings-watcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.knolss.meetings-watcher.plist
```

## Limitations (MVP)

- Main display only
- First matching meeting per poll tick if several overlap
- No Teams link / attendees — title and start time only
