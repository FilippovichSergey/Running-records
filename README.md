# Sergey's Running Log

A personal running log with a visual HTML dashboard and a GUI script for adding and editing events.

---

## Project structure

```
Running records/
├── index.html             # Dashboard markup + styles — open in a browser to view your log
├── app.js                 # Dashboard logic (external, so a strict CSP can forbid inline scripts)
├── vercel.json            # Security headers (Content-Security-Policy, etc.) for the hosted site
├── add_new_event.py       # GUI script for managing runs and personal bests
├── run.bat                # Shortcut to launch the script on Windows
├── process_activities.py  # Processes Garmin CSV exports into data/activities.js
├── process_activities.bat # Shortcut to run the processor on Windows
├── fetch_strava.py        # Optional: pull activities from the Strava API
├── fetch_garmin.py        # Optional: pull activities from Garmin Connect
├── resize_images.py       # Optional: batch-resize photos with ImageMagick
├── make_previews.py       # Generates the small WebP previews the dashboard displays
├── make_previews.bat      # Shortcut to run the preview generator on Windows
└── data/
    ├── data.js            # Auto-generated — do not edit manually
    ├── activities.js      # Auto-generated — do not edit manually
    ├── photo-dims.js      # Auto-generated — image sizes, so cells reserve the right box
    ├── sneakers.json      # Persistent list of sneaker names for the dropdown
    ├── runs/              # One JSON file per run
    ├── pbs/               # One JSON file per personal best distance
    ├── activities/        # Garmin CSV exports (drop files here, then run processor)
    ├── photos/            # Original photos, organised by event — the lightbox opens these
    └── previews/          # Auto-generated WebP previews (micro / thumb / card)
```

---

## Viewing the log

Open `index.html` in any browser. No server required.

- **Overview** tab — the landing page. A full-bleed hero photo with your lifetime totals (distance raced, elevation climbed, longest race, fastest 5K), a *Race memories* masonry of photos, and a *Latest race* card. All figures are computed from your data, not hardcoded.
- **All Runs** tab — competition runs sorted newest first. Each card opens with a photo strip and an overlapping medal, then the race name, distance, distance-type tags (⚡ Sprint · 🏃 Mid · 🏅 Long · 🎽 Marathon · 🏔 Ultra · 🌿 Trail) and a four-column stat rail (pace / climb / avg HR / time). Filter by year, distance (`< 5 km`, `5 – 9.99 km`, `10 – 42 km`, `> 42 km`, or `Custom` for an exact figure), location, race name, or trail. Choosing a year narrows the other dropdowns to the values that actually occur in it. Clicking any photo opens it full size.
- **Personal Bests** tab — best time per distance with pace, heart rate, sneakers, and previous records. A progression bar chart shows how the time came down over the years, and an expandable trend chart plots pace or time for a chosen distance.
- **Activities** tab — all training activities imported from Garmin. Bar chart with selectable activity type, metric (distance / runs / time), and period. Summary strip shows totals and averages. Text search and year quick-jump buttons filter the list without leaving the tab.
- **EN / BE** toggle in the top-right corner switches the interface between English and Belarusian, including dates, labels, and location names. Belarusian is the default.
- **☀ / ☽** toggle switches between light and dark mode. Both choices are remembered in the browser.

---

## Managing events

Run the GUI script:

```
run.bat
```

or directly:

```
python add_new_event.py
```

The script has five tabs: **Add Run**, **Add Personal Best**, **Edit Run**, **Edit Personal Best**, and **View All**.

### Add Run tab

| Field | Format |
|---|---|
| Date | YYYY-MM-DD |
| Race name | Name of the race, e.g. `Mestia Ultra` — shown as the card title |
| Location (EN) | English name, e.g. `Batumi` |
| Location (BE) | Belarusian name, e.g. `Батумі` |
| Country (EN) | English name, e.g. `Georgia` |
| Country (BE) | Belarusian name, e.g. `Грузія` |
| Distance | Kilometres, e.g. `12.4` |
| Total time | H:MM:SS, e.g. `1:05:30` |
| Avg HR | Beats per minute |
| Max HR | Beats per minute |
| Elevation | Metres of elevation gain, e.g. `320`. Use `0` if flat |
| Sneakers | Choose from dropdown or type a new name |
| Video link | Optional URL shown in the Photos section |
| Photos folder | Optional — all images in the folder are copied into `data/photos/` |
| Medal photo | Optional — single image copied as `data/photos/<event>/medal.<ext>` and shown on the card |

### Add Personal Best tab

| Field | Format |
|---|---|
| Distance label | Display name, e.g. `5 km` or `Half Marathon` |
| Distance (km) | Numeric, e.g. `5` or `21.0975` — used to calculate pace |
| Total time | H:MM:SS, e.g. `19:14` |
| Date | YYYY-MM-DD |
| Race name | Name of the race |
| Location (EN) | English name |
| Location (BE) | Belarusian name |
| Country (EN) | English name |
| Country (BE) | Belarusian name |
| Avg HR | Beats per minute |
| Max HR | Beats per minute |
| Sneakers | Choose from dropdown or type a new name |
| Video link | Optional URL shown in the Photos section |
| Photos folder | Optional |
| Medal photo | Optional — single image shown on the PB card |
| Previous records | One record per line: `time\|date\|location` |

### Edit Run / Edit Personal Best tabs

Select an event from the list — all fields populate automatically. Change any field and click **Save Changes**. If the date is changed, the old JSON file is renamed accordingly. To add more photos, specify a folder; existing photos are preserved. Click **Delete** to permanently remove the event (confirmation required).

### Sneakers

The Sneakers field is a dropdown backed by `data/sneakers.json`. Typing a new name and saving adds it to the list automatically — it appears in the dropdown on the next use.

### After saving

The script writes a JSON file to `data/runs/` or `data/pbs/`, regenerates `data/data.js`, and then regenerates the photo previews (see below). Refresh the browser to see the updated log.

If ImageMagick is missing the save still succeeds — you will just see a warning, and can run `make_previews.bat` later.

---

## Activities tab

The Activities tab shows all training runs imported from Garmin Connect.

### Importing activity data

1. In Garmin Connect, export your activities as a CSV file.
2. Drop the file into `data/activities/`.
3. Run the processor:

```
process_activities.bat
```

or directly:

```
python process_activities.py
```

This merges all CSV files in the folder, filters to running activity types only, and writes `data/activities.js`. If two files contain the same activity, the one from the latest-modified file is used.

Refresh the browser to see the updated Activities tab.

### Supported activity types

Running, Trail Running, Track Running, Indoor Running, Street Running, Treadmill Running, Ultra Running, Virtual Running, Obstacle Course Racing.

### Period options

| Period | Range |
|---|---|
| Last 7 days | Rolling 7-day window ending today |
| This month | Current calendar month |
| Last month | Rolling 30-day window ending today |
| This year | Current calendar year |
| Last year | Rolling 365-day window ending today |
| All years | All recorded activities |
| Custom | Pick a start and end date |

### Chart

The bar chart auto-selects granularity based on the period length: daily (≤ 31 days), weekly (≤ 90 days), monthly (≤ 3 years), yearly (> 3 years). Empty years are hidden when using yearly granularity.

### Summary strip

Shows totals for the selected period: number of runs, total distance, total time, period duration, and average km per week / month / year (each shown only when the period is long enough).

### Search and year navigation

A text search box above the activity list filters by activity type (e.g. `trail`) or date fragment (e.g. `2025-03`). Year buttons are generated from the data — clicking one jumps to that calendar year as a custom date range. Switching back to a preset period clears the year selection.

---

## Data files

Each event is stored as a standalone JSON file:

**Run** (`data/runs/YYYY-MM-DD.json`):
```json
{
  "date": "2026-05-31",
  "race_name": "Gorky Park Half",
  "location": "Gorky Park",
  "location_be": "Парк Горкага",
  "country": "Georgia",
  "country_be": "Грузія",
  "distance_km": 10.0,
  "total_time": "51:30",
  "hr_avg": 145,
  "hr_max": 168,
  "elevation": 120,
  "sneakers": "Nike Vaporfly 4",
  "video": "https://youtube.com/...",
  "photos": ["data/photos/2026-05-31/IMG_001.jpg"],
  "medal": "data/photos/2026-05-31/medal.jpg"
}
```

**Personal Best** (`data/pbs/5_km.json`):
```json
{
  "distance": "5 km",
  "distance_km": 5.0,
  "total_time": "19:14",
  "date": "2026-05-31",
  "race_name": "Poti Marathon 2026",
  "location": "Poti",
  "location_be": "Поці",
  "country": "Georgia",
  "country_be": "Грузія",
  "hr_avg": 171,
  "hr_max": 182,
  "sneakers": "Nike Vaporfly 4",
  "video": "https://youtube.com/...",
  "photos": [],
  "medal": "data/photos/pb_5_km/medal.jpg",
  "previous_records": [
    { "time": "19:36", "date": "2024-04-27", "location": "Батумі" }
  ]
}
```

**Notes:**
- `location_be` is optional — if absent, the English `location` is shown in both language modes.
- `race_name`, `country`, `country_be`, `video` and `medal` are optional — omit the key entirely if not set.
- Photo and medal paths point at the ORIGINAL image. The dashboard derives the preview path from it automatically (see Photos and previews).
- Pace is calculated from `distance_km` and `total_time` — it is not stored.
- Elevation `0` is shown only in the expanded details panel, not in the stats row.

---

## Photos and previews

Photos are stored full-size in `data/photos/`, but the dashboard never displays them
directly — a 2500px photo rendered into a 200px cell wastes several hundred KB each.
Instead `make_previews.py` renders small WebP previews and the page loads those. The
lightbox still opens the untouched original.

### Generating previews

```
make_previews.bat
```

or directly:

```
python make_previews.py
```

It runs automatically after every save in the event editor, so you normally never need
to call it by hand. Run it manually after a fresh clone, or if you hand-edit the JSON
files. It requires ImageMagick 7 (`magick` on PATH).

| Flag | Effect |
|---|---|
| `--force` | Re-encode everything, even if up to date |
| `--dry-run` | Print the plan without writing anything |
| `--prune` | Delete previews whose source is no longer referenced |
| `--jobs N` | Limit parallelism (default: 8) |

### How it works

It reads the image paths out of `data/data.js`, so coverage is exactly 1:1 with what the
site requests and no preview can be missing. Each image is rendered at three widths:

| Tier | Width | Used for |
|---|---|---|
| `micro` | 256 px | 64px medal badges |
| `thumb` | 640 px | Overview grid, strip cells, Personal Bests grid |
| `card` | 1280 px | Large Overview cells, first strip cell, the hero |

Previews are shrink-only, so an image smaller than the tier passes through untouched, and
EXIF rotation is applied before metadata is stripped. Output lands in
`data/previews/<tier>/….webp`, mirroring the source path.

It also writes `data/photo-dims.js` with each image's natural size. The dashboard puts
those on the `<img>` as `width`/`height`, so every cell reserves the correct box before
the image loads and the layout does not jump.

### Layout

Photo cells take their own photo's aspect ratio — nothing is cropped or stretched. The
Overview memories grid is a masonry, and the All Runs strip is a fixed-height row where
each photo keeps its natural width. Medals are the deliberate exception: they use
`object-fit: cover` so the circular badge is filled.

The medal badge on a run card is positioned at `bottom: -26px`, so it deliberately
overhangs the photo strip into the card body. **`.rc-strip` must therefore not set
`overflow: hidden`** — that clips the badge into a half circle. It is not needed anyway:
strip photos are `flex: 0 1 auto` with `min-width: 0`, so they shrink to fit rather than
overflow. The rounded corners come from `overflow: hidden` on `.run-card` instead.

Both `data/photos/` and `data/previews/` are committed, because the deployed site serves
the previews and the lightbox serves the originals.

---

## Security

The site is static (HTML + JS + JSON) with no backend, no database, and no third-party frontend libraries, so the attack surface is small. The following measures harden it further.

### Content-Security-Policy and HTTP headers

`vercel.json` sets a strict CSP and companion headers on every response:

| Header | Value / effect |
|---|---|
| `Content-Security-Policy` | `default-src 'self'`; `script-src 'self'` (no `unsafe-inline` — inline scripts cannot execute); `style-src 'self' 'unsafe-inline'`; `img-src 'self' data:`; `connect-src 'self'`; `object-src 'none'`; `base-uri 'self'`; `frame-ancestors 'none'`; `upgrade-insecure-requests` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` (anti-clickjacking, alongside `frame-ancestors 'none'`) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | camera / microphone / geolocation disabled |

Because `script-src` is `'self'` with no `'unsafe-inline'`, all JavaScript lives in `app.js` and there are **no inline event handlers** — the dashboard wires events with `addEventListener` and a delegated `data-action` click handler. This means an injected `<script>` or `onerror=` attribute cannot run.

### Output escaping (XSS)

All user-authored data (race name, location, sneakers, times, photo/medal paths, activity type) is HTML-escaped with an `esc()` helper before it is inserted into the DOM. Video links are passed through `safeUrl()`, which allows only `http(s)://` URLs — `javascript:` / `data:` links are neutralised.

### Credentials and secrets

- `fetch_strava.py` and `fetch_garmin.py` store credentials and OAuth tokens in local files only. These are git-ignored and must never be committed:
  `garmin_credentials.json`, `strava_credentials.json`, `strava_token.json`, `.garmin_tokens/`.
- No secrets are hardcoded in the code, and secret values are never printed to stdout (passwords are read with `getpass`).
- TLS verification is left at the secure default (no `verify=False`); subprocess calls use argument lists (no `shell=True`).

### Keeping dependencies current

The optional sync scripts depend on `requests` and (for Garmin) `garminconnect`. There is no `requirements.txt`, so pin/update deliberately and run an audit periodically:

```
pip install pip-audit
pip-audit
```
