# Sergey's Running Log

A personal running log with a visual HTML dashboard and a GUI script for adding and editing events.

---

## Project structure

```
Running records/
├── running-log.html       # Dashboard — open in a browser to view your log
├── add_new_event.py       # GUI script for managing runs and personal bests
├── run.bat                # Shortcut to launch the script on Windows
└── data/
    ├── data.js            # Auto-generated — do not edit manually
    ├── sneakers.json      # Persistent list of sneaker names for the dropdown
    ├── runs/              # One JSON file per run
    ├── pbs/               # One JSON file per personal best distance
    └── photos/            # Photos copied from source folders, organised by event
```

---

## Viewing the log

Open `running-log.html` in any browser. No server required.

- **All Runs** tab — cards sorted newest first. Each card shows pace, avg HR, and total time. If elevation gain is recorded, it appears as a fourth stat. Expand a card for full details and photos.
- **Personal Bests** tab — best time per distance with pace, heart rate, sneakers, and previous records.
- **EN / BE** toggle in the top-right corner switches the interface between English and Belarusian, including dates, labels, and location names.

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
| Location (EN) | English name, e.g. `Batumi` |
| Location (BE) | Belarusian name, e.g. `Батумі` |
| Distance | Kilometres, e.g. `12.4` |
| Total time | H:MM:SS, e.g. `1:05:30` |
| Avg HR | Beats per minute |
| Max HR | Beats per minute |
| Elevation | Metres of elevation gain, e.g. `320`. Use `0` if flat |
| Sneakers | Choose from dropdown or type a new name |
| Photos folder | Optional — all images in the folder are copied into `data/photos/` |

### Add Personal Best tab

| Field | Format |
|---|---|
| Distance label | Display name, e.g. `5 km` or `Half Marathon` |
| Distance (km) | Numeric, e.g. `5` or `21.0975` — used to calculate pace |
| Total time | H:MM:SS, e.g. `19:14` |
| Date | YYYY-MM-DD |
| Location (EN) | English name |
| Location (BE) | Belarusian name |
| Avg HR | Beats per minute |
| Max HR | Beats per minute |
| Sneakers | Choose from dropdown or type a new name |
| Photos folder | Optional |
| Previous records | One record per line: `time\|date\|location` |

### Edit Run / Edit Personal Best tabs

Select an event from the list — all fields populate automatically. Change any field and click **Save Changes**. If the date is changed, the old JSON file is renamed accordingly. To add more photos, specify a folder; existing photos are preserved. Click **Delete** to permanently remove the event (confirmation required).

### Sneakers

The Sneakers field is a dropdown backed by `data/sneakers.json`. Typing a new name and saving adds it to the list automatically — it appears in the dropdown on the next use.

### After saving

The script writes a JSON file to `data/runs/` or `data/pbs/` and regenerates `data/data.js`. Refresh the browser to see the updated log.

---

## Data files

Each event is stored as a standalone JSON file:

**Run** (`data/runs/YYYY-MM-DD.json`):
```json
{
  "date": "2026-05-31",
  "location": "Gorky Park",
  "location_be": "Парк Горкага",
  "distance_km": 10.0,
  "total_time": "51:30",
  "hr_avg": 145,
  "hr_max": 168,
  "elevation": 120,
  "sneakers": "Nike Vaporfly 4",
  "photos": ["data/photos/2026-05-31/IMG_001.jpg"]
}
```

**Personal Best** (`data/pbs/5_km.json`):
```json
{
  "distance": "5 km",
  "distance_km": 5.0,
  "total_time": "19:14",
  "date": "2026-05-31",
  "location": "Poti",
  "location_be": "Поці",
  "hr_avg": 171,
  "hr_max": 182,
  "sneakers": "Nike Vaporfly 4",
  "photos": [],
  "previous_records": [
    { "time": "19:36", "date": "2024-04-27", "location": "Батумі" }
  ]
}
```

**Notes:**
- `location_be` is optional — if absent, the English `location` is shown in both language modes.
- Pace is calculated from `distance_km` and `total_time` — it is not stored.
- Elevation `0` is shown only in the expanded details panel, not in the stats row.
