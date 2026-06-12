# Sergey's Running Log

A personal running log with a visual HTML dashboard and a GUI script for adding events.

---

## Project structure

```
Running records/
├── running-log.html       # Dashboard — open in a browser to view your log
├── add_new_event.py       # GUI script for adding runs and personal bests
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

- **All Runs** tab — cards sorted newest first, each showing pace, avg HR, and total time. Expand a card to see full details and photos.
- **Personal Bests** tab — best time per distance with pace, heart rate, and previous records.
- **EN / BE** toggle in the top-right corner switches the interface language between English and Belarusian.

---

## Adding events

Run the GUI script:

```
run.bat
```

or directly:

```
python add_new_event.py
```

### Add Run tab

| Field | Format |
|---|---|
| Date | YYYY-MM-DD |
| Location | Free text |
| Distance | Kilometres, e.g. `12.4` |
| Total time | H:MM:SS, e.g. `1:05:30` |
| Avg HR | Beats per minute |
| Max HR | Beats per minute |
| Sneakers | Choose from dropdown or type a new name |
| Photos folder | Optional — all images in the folder are copied into `data/photos/` |

### Add Personal Best tab

Same fields as Add Run, plus:

| Field | Format |
|---|---|
| Distance label | Display name, e.g. `5 km` or `Half Marathon` |
| Distance (km) | Numeric, e.g. `5` or `21.0975` — used to calculate pace |
| Previous records | One record per line: `time\|date\|location` |

### Sneakers

The Sneakers field is a dropdown backed by `data/sneakers.json`. Typing a new name and saving adds it to the list automatically — it will appear in the dropdown on the next use.

### After saving

The script writes a JSON file to `data/runs/` or `data/pbs/` and regenerates `data/data.js`. Refresh the browser to see the new entry.

---

## Data files

Each event is stored as a standalone JSON file:

**Run** (`data/runs/YYYY-MM-DD.json`):
```json
{
  "date": "2026-05-31",
  "location": "Gorky Park, Moscow",
  "distance_km": 10.0,
  "total_time": "51:30",
  "hr_avg": 145,
  "hr_max": 168,
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
  "location": "Поці",
  "hr_avg": 171,
  "hr_max": 182,
  "sneakers": "Nike Vaporfly 4",
  "photos": [],
  "previous_records": [
    { "time": "19:36", "date": "2024-04-27", "location": "Батумі" }
  ]
}
```

Pace is calculated automatically from `distance_km` and `total_time` — it is not stored.
