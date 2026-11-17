# Dark Souls Meeting Notifications

Full-width overlay strip **2 minutes before** calendar meetings, Dark Souls style. Reads **Apple Calendar** via EventKit (including calendars synced from corporate Outlook). **VPN is not required** — only Calendar sync on your Mac matters.

## Menu bar app (recommended)

### Build `.app`

```bash
git clone https://github.com/tearsdontfall/dark_souls_notifications.git
cd dark_souls_notifications
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[build]"
python setup_app.py py2app
```

Output: `macos_app/dist/Dark Souls Meetings.app`

Copy to Applications:

```bash
cp -r "macos_app/dist/Dark Souls Meetings.app" /Applications/
```

Launch by double-clicking. The app lives in the **menu bar** (⚔), with no Dock icon and no Terminal window.

### First launch

1. macOS asks for **Calendar** access — allow it for **Dark Souls Meetings** (not Terminal).
2. A window opens to **select calendars** (checkboxes). Click **Save**.
3. The watcher starts automatically. Menu shows `● Watching` and the next meeting.

### Menu bar actions

| Item | Action |
|------|--------|
| ● Watching / ○ Paused | Current status |
| Next: … | Nearest meeting in the next 2 hours |
| Pause / Resume | Stop or resume polling |
| Test notification | Preview the overlay strip |
| Select calendars… | Re-open calendar picker |
| Set notification sound… | Pick audio file, test, or disable sound |
| Sound: … | Current sound file (read-only) |
| Open config folder | Edit `config.json` manually |
| Show log in Finder | `~/.cache/dark-souls-meetings/app.log` |
| Quit | Exit the app |

### Calendar permission migration

If you previously used the Terminal watcher, grant Calendar access to **Dark Souls Meetings** in **System Settings → Privacy & Security → Calendar**. You can revoke access for Terminal/Python if no longer needed.

### Auto-start at login

```bash
mkdir -p ~/Library/LaunchAgents
cp scripts/com.example.meetings-watcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.example.meetings-watcher.plist
```

The plist expects the app at `/Applications/Dark Souls Meetings.app`. Edit the path if you installed elsewhere. Use an absolute path: `launchd` does not expand `~` or `$HOME` in plist fields.

## Dev mode (Terminal)

```bash
pip install -e .
python -m notifications app      # menu bar from Python (for development)
python -m notifications setup    # terminal calendar picker
python -m notifications watch    # terminal-only watcher
```

Config: `~/.config/dark-souls-meetings/config.json`

## Config

See [`config.example.json`](config.example.json):

| Field | Default | Description |
|-------|---------|-------------|
| `calendar_ids` | from setup | EventKit calendar identifiers |
| `minutes_before` | 2 | Target minutes before start |
| `poll_interval_seconds` | 30 | Poll interval |
| `overlay_duration_seconds` | 5 | How long the strip stays visible |
| `sound_path` | `null` | Path to audio file for `afplay` |

## Custom sound

**From the menu bar:** **Set notification sound…** → choose a file → **Test sound** → **Save**.

Supported formats: `.wav`, `.mp3`, `.aiff`, `.m4a`, `.caf`, `.aac`. A good place to store files:

```text
~/.config/dark-souls-meetings/sounds/summon.wav
```

**Disable sound:** **Disable sound** → **Save**, or set `"sound_path": null` in `config.json`.

Changes apply immediately — no restart needed.

## Test

1. Create a test event in Calendar **3–4 minutes** from now.
2. Run the app (`.app` or `python -m notifications app`).
3. About **2 minutes** before start, the centered strip appears.

Dedup cache: `~/.cache/dark-souls-meetings/notified.json` — restarting won't re-notify the same event.

## Requirements

- macOS with Apple Calendar
- Python 3.11+ (for building; the `.app` bundles its own runtime)
- Calendar permission for the app

Screen Recording and Accessibility are **not** required.

## Limitations

- Main display only
- First matching meeting per poll if several overlap
- Setup GUI selects calendars; sound via menu or config folder
