"""
Running Log – Event Editor
Adds/edits runs and personal bests.
Saves individual JSON files → data/runs/ or data/pbs/
Regenerates data/data.js for running-log.html.

Every save runs in the same order, so a failure part-way can never lose a record:
  1. validate every field (all problems are reported together);
  2. check for clashes with other records, and ask before touching them;
  3. copy the medal/photos (never overwriting a different file);
  4. write the JSON atomically (temp file + os.replace);
  5. only then remove the old file, if the record was renamed.
"""

import filecmp
import json
import math
import os
import re
import shutil
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import date
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent
DATA_DIR      = BASE_DIR / "data"
RUNS_DIR      = DATA_DIR / "runs"
PBS_DIR       = DATA_DIR / "pbs"
PHOTOS_DIR    = DATA_DIR / "photos"
DATA_JS       = DATA_DIR / "data.js"
SNEAKERS_FILE = DATA_DIR / "sneakers.json"

for d in (RUNS_DIR, PBS_DIR, PHOTOS_DIR):
    d.mkdir(parents=True, exist_ok=True)

IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}


class ValidationError(ValueError):
    """A problem with what was typed into the form. Raised before anything is written."""


class Checker:
    """Runs field parsers, collecting every error so one dialog can list them all."""

    def __init__(self):
        self.errors = []

    def __call__(self, parse, *args):
        try:
            return parse(*args)
        except ValidationError as e:
            self.errors.append(str(e))
            return None

    def raise_if_any(self):
        if self.errors:
            raise ValidationError("\n".join(self.errors))


# ── Field parsing ─────────────────────────────────────────────────────────────
# re.ASCII everywhere: a bare \d also matches Arabic-Indic and other Unicode digits.

_DATE_RE  = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_TIME_RE  = re.compile(r"(?:(\d+):)?(\d+):(\d\d(?:\.\d{1,3})?)", re.ASCII)
_DIST_RE  = re.compile(r"\d+(?:\.\d+)?", re.ASCII)
_COUNT_RE = re.compile(r"\d+", re.ASCII)


def parse_date(text: str, field: str = "Date") -> str:
    """A real calendar date as canonical YYYY-MM-DD (it also names the run's file)."""
    s = text.strip()
    if not s:
        raise ValidationError(f"{field} is required.")
    if _DATE_RE.fullmatch(s):
        try:
            date.fromisoformat(s)
            return s
        except ValueError:
            pass
    raise ValidationError(f'{field}: "{s}" is not a real date — use YYYY-MM-DD, e.g. 2026-05-31.')


def time_to_sec(s: str) -> float:
    """Same arithmetic as timeToSec() in app.js."""
    p = [float(x) for x in s.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def parse_time(text: str, field: str = "Total time") -> str:
    """H:MM:SS or M:SS, kept as typed. Track results may carry a fraction: 0:00:27.4."""
    s = text.strip()
    if not s:
        raise ValidationError(f"{field} is required.")
    m = _TIME_RE.fullmatch(s)
    if m:
        hours, minutes, seconds = m.groups()
        if (float(seconds) < 60
                and (hours is None or (len(minutes) == 2 and int(minutes) < 60))
                and time_to_sec(s) > 0):
            return s
    raise ValidationError(f'{field}: "{s}" is not a time — use H:MM:SS or M:SS, e.g. 1:05:30 or 19:14.')


def parse_distance(text: str, field: str = "Distance (km)") -> float:
    s = text.strip().replace(",", ".")
    if not s:
        raise ValidationError(f"{field} is required.")
    if _DIST_RE.fullmatch(s):
        km = float(s)
        if math.isfinite(km) and km > 0:
            return km
    raise ValidationError(f'{field}: "{text.strip()}" must be a positive number, e.g. 10 or 21.1.')


def parse_count(text: str, field: str) -> int:
    """Heart rate: a whole number ≥ 0. Empty means 0 (not recorded)."""
    s = text.strip()
    if not s:
        return 0
    if _COUNT_RE.fullmatch(s):
        return int(s)
    raise ValidationError(f'{field}: "{s}" must be a whole number (or left empty).')


def parse_elevation(text: str, field: str = "Elevation") -> int | float:
    """Metres of climb ≥ 0. Empty means 0. A fraction is kept as it is (a GPS import
    may give 12.5); a whole number is stored as an int, like the form always did."""
    s = text.strip().replace(",", ".")
    if not s:
        return 0
    if _DIST_RE.fullmatch(s):
        m = float(s)
        if math.isfinite(m):
            return int(m) if m.is_integer() else m
    raise ValidationError(f'{field}: "{text.strip()}" must be a number of metres ≥ 0 (or left empty).')


def number_text(v) -> str:
    """A stored number as a form field shows it. 150.0 becomes "150", so a whole value
    saved as a float (by hand or by an import) still passes parse_count unchanged."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


_WIN_RESERVED = {"con", "prn", "aux", "nul",
                 *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def pb_slug(label: str) -> str:
    """File id of a personal best: "5 km" -> "5_km" (data/pbs/5_km.json, photos in pb_5_km/).

    The transform is unchanged, so existing files keep their names. A label that would
    not give one safe file name (path separators, "..", reserved names) is refused.
    """
    if not label.strip():
        raise ValidationError("Distance label is required.")
    slug = label.strip().lower().replace(" ", "_").replace("/", "")
    if (not slug.strip(".") or slug.endswith(".")
            or any(c in '\\:*?"<>|' or ord(c) < 32 for c in slug)
            or slug.split(".")[0] in _WIN_RESERVED):
        raise ValidationError(f'Distance label: "{label.strip()}" can\'t be used as a file name — '
                              'avoid \\ : * ? " < > | and a trailing dot.')
    return slug


def child_path(folder: Path, name: str) -> Path:
    """folder/name, refusing anything that would land outside folder."""
    path = folder / name
    if Path(name).name != name or path.resolve().parent != folder.resolve():
        raise ValidationError(f'"{name}" is not a plain file name.')
    return path


def parse_previous_records(text: str) -> list[dict]:
    """PB history, one "time|date|location" per line.

    Every non-empty line must parse: a bad line is reported with its number instead of
    being silently dropped on save. Only the first two "|" split, so a location may
    itself contain "|".
    """
    records, errors = [], []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) != 3:
            errors.append(f'line {n}: "{line.strip()}" — expected time|date|location')
            continue
        chk = Checker()
        t = chk(parse_time, parts[0], "time")
        d = chk(parse_date, parts[1], "date")
        if chk.errors:
            errors.append(f"line {n}: " + "; ".join(chk.errors))
            continue
        records.append({"time": t, "date": d, "location": parts[2]})
    if errors:
        raise ValidationError("Previous records:\n  " + "\n  ".join(errors))
    return records


def run_form(t) -> dict:
    """Raw strings from a run form — Add Run and Edit Run use the same widget names."""
    return {
        "date": t.v_date.get(), "race_name": t.v_race.get(),
        "location": t.v_location.get(), "location_be": t.v_location_be.get(),
        "country": t.v_country.get(), "country_be": t.v_country_be.get(),
        "distance_km": t.v_dist.get(), "total_time": t.v_total_time.get(),
        "hr_avg": t.v_hr_avg.get(), "hr_max": t.v_hr_max.get(),
        "elevation": t.v_elevation.get(),
        "sneakers": t.v_sneakers.get(), "video": t.v_video.get(),
    }


def pb_form(t) -> dict:
    """Raw strings from a PB form — Add and Edit Personal Best use the same widget names."""
    return {
        "distance": t.v_distance.get(), "distance_km": t.v_distance_km.get(),
        "total_time": t.v_total_time.get(), "date": t.v_date.get(),
        "race_name": t.v_race.get(),
        "location": t.v_location.get(), "location_be": t.v_location_be.get(),
        "country": t.v_country.get(), "country_be": t.v_country_be.get(),
        "hr_avg": t.v_hr_avg.get(), "hr_max": t.v_hr_max.get(),
        "sneakers": t.v_sneakers.get(), "video": t.v_video.get(),
        "previous_records": t.prev_text.get("1.0", "end"),
    }


def validate_run(raw: dict, chk: Checker) -> dict:
    """A run record from raw form strings; medal/photos are filled in by the caller."""
    return {
        "date":        chk(parse_date, raw["date"]),
        "race_name":   raw["race_name"].strip(),
        "location":    raw["location"].strip(),
        "location_be": raw["location_be"].strip(),
        "country":     raw["country"].strip(),
        "country_be":  raw["country_be"].strip(),
        "distance_km": chk(parse_distance, raw["distance_km"]),
        "total_time":  chk(parse_time, raw["total_time"]),
        "hr_avg":      chk(parse_count, raw["hr_avg"], "Avg HR"),
        "hr_max":      chk(parse_count, raw["hr_max"], "Max HR"),
        "elevation":   chk(parse_elevation, raw["elevation"]),
        "sneakers":    raw["sneakers"].strip(),
        "video":       raw["video"].strip(),
        "medal":       "",
        "photos":      [],
    }


def validate_pb(raw: dict, chk: Checker) -> dict:
    """A PB record from raw form strings; medal/photos are filled in by the caller."""
    label = raw["distance"].strip()
    chk(pb_slug, label)
    return {
        "distance":         label,
        "distance_km":      chk(parse_distance, raw["distance_km"]),
        "total_time":       chk(parse_time, raw["total_time"]),
        "date":             chk(parse_date, raw["date"]),
        "race_name":        raw["race_name"].strip(),
        "location":         raw["location"].strip(),
        "location_be":      raw["location_be"].strip(),
        "country":          raw["country"].strip(),
        "country_be":       raw["country_be"].strip(),
        "hr_avg":           chk(parse_count, raw["hr_avg"], "Avg HR"),
        "hr_max":           chk(parse_count, raw["hr_max"], "Max HR"),
        "sneakers":         raw["sneakers"].strip(),
        "video":            raw["video"].strip(),
        "medal":            "",
        "photos":           [],
        "previous_records": chk(parse_previous_records, raw["previous_records"]),
    }


# ── JSON helpers ──────────────────────────────────────────────────────────────

def read_json(path: Path):
    return json.loads(path.read_text("utf-8-sig"))   # utf-8-sig tolerates a BOM


_TEXT_FIELDS  = ("id", "race_name", "location", "location_be", "country", "country_be",
                 "sneakers", "video", "medal")
_HR_FIELDS    = ("hr_avg", "hr_max")


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def record_problem(rec, kind: str) -> str | None:
    """Why a loaded run ("run") or personal best ("pb") can't be used, or None.

    Checks what the editor and the site rely on: the required fields, their types,
    real dates and times, and the shape of photos / previous_records. A file failing
    this is skipped, instead of crashing the editor with a KeyError further on.
    """
    if not isinstance(rec, dict):
        return "not a JSON object"
    required = ("distance",) * (kind == "pb") + ("date", "distance_km", "total_time")
    missing = [k for k in required if k not in rec]
    if missing:
        return "missing " + ", ".join(f'"{k}"' for k in missing)
    for k in ("date", "total_time") + ("distance",) * (kind == "pb"):
        if not isinstance(rec[k], str):
            return f'"{k}" must be text'
    try:
        parse_date(rec["date"], '"date"')
        parse_time(rec["total_time"], '"total_time"')
    except ValidationError as e:
        return str(e)
    if kind == "pb" and not rec["distance"].strip():
        return '"distance" is empty'
    if not _is_number(rec["distance_km"]) or rec["distance_km"] <= 0:
        return '"distance_km" must be a number above 0'
    for k in _TEXT_FIELDS:
        if k in rec and not isinstance(rec[k], str):
            return f'"{k}" must be text'
    # The same rules as the form (parse_count / parse_elevation), so every record that
    # loads can also be saved again without touching these fields.
    for k in _HR_FIELDS:
        if k in rec and not (_is_number(rec[k]) and rec[k] >= 0 and float(rec[k]).is_integer()):
            return f'"{k}" must be a whole number ≥ 0'
    if "elevation" in rec and not (_is_number(rec["elevation"]) and rec["elevation"] >= 0):
        return '"elevation" must be a number ≥ 0'
    if "photos" in rec and not (isinstance(rec["photos"], list)
                                and all(isinstance(p, str) for p in rec["photos"])):
        return '"photos" must be a list of paths'
    if "previous_records" in rec:
        hist = rec["previous_records"]
        if not isinstance(hist, list):
            return '"previous_records" must be a list'
        for i, r in enumerate(hist, 1):
            if not (isinstance(r, dict) and isinstance(r.get("time"), str)
                    and isinstance(r.get("date"), str) and isinstance(r.get("location", ""), str)):
                return f"previous_records #{i} needs text time, date and location"
            try:
                parse_time(r["time"], f"previous_records #{i} time")
                parse_date(r["date"], f"previous_records #{i} date")
            except ValidationError as e:
                return str(e)
    return None


def scan_records(folder: Path, kind: str) -> tuple[list[dict], list[str]]:
    """(usable records, ["runs/x.json: why it was skipped", ...]) for one folder."""
    records, problems = [], []
    for f in sorted(folder.glob("*.json")):
        try:
            data = read_json(f)
        except (OSError, ValueError) as e:
            problems.append(f"{folder.name}/{f.name}: not readable JSON ({e})")
            continue
        issue = record_problem(data, kind)
        if issue:
            problems.append(f"{folder.name}/{f.name}: {issue}")
            continue
        data["_path"] = f          # the real file: edits and deletes act on this one
        records.append(data)
    return records, problems


def load_all_runs():
    return scan_records(RUNS_DIR, "run")[0]


def load_all_pbs():
    return scan_records(PBS_DIR, "pb")[0]


def load_problems() -> list[str]:
    return scan_records(RUNS_DIR, "run")[1] + scan_records(PBS_DIR, "pb")[1]


class DataError(ValueError):
    """Some record files can't be loaded, so data.js must not be rebuilt without them."""


def run_target(run_date: str, old: dict | None = None) -> tuple[Path, list[dict]]:
    """The file a run on run_date is written to, and the other runs already on that day.

    An edited run that keeps its date keeps its own file, whatever its name. Otherwise
    the first free name is taken — 2026-06-01.json, then 2026-06-01_2.json — so a
    second run on the same day never replaces the first.
    """
    if old is not None and old.get("date") == run_date:
        return old["_path"], []
    own = old["_path"] if old is not None else None
    others = [r for r in load_all_runs() if r.get("date") == run_date and r["_path"] != own]
    path, n = child_path(RUNS_DIR, f"{run_date}.json"), 1
    while path.exists() and path != own:
        n += 1
        path = child_path(RUNS_DIR, f"{run_date}_{n}.json")
    return path, others


def published_ids(runs: list[dict] | None = None) -> dict[Path, str]:
    """Each run file's Atom entry id, decided exactly as make_feed.py publishes it."""
    import make_feed
    return {r["_path"]: key for r, key in make_feed.assign_ids(load_all_runs() if runs is None else runs)}


def new_run_id(run_date: str) -> str:
    """Feed id for a new run: its date, or <date>-2, -3… when that is taken — also by a
    run that has since moved to another date and kept the id it was published under."""
    taken = set(published_ids().values())
    rid, n = run_date, 1
    while rid in taken:
        n += 1
        rid = f"{run_date}-{n}"
    return rid


def freeze_feed_ids() -> list[str]:
    """Store "id" in every run whose published feed id is not simply its date — e.g. a
    hand-made <date>_2.json. Otherwise deleting or moving another run that day would
    shift its id. The editor's own saves never need this. Returns the files changed."""
    runs = load_all_runs()
    changed = []
    for path, key in published_ids(runs).items():
        run = next(r for r in runs if r["_path"] == path)
        if key != run["date"] and str(run.get("id") or "") != key:
            record = {k: v for k, v in run.items() if not k.startswith("_") and k != "id"}
            write_json(path, {"id": key, **record})
            changed.append(path.name)
    return changed


def _label_slug(pb: dict) -> str | None:
    try:
        return pb_slug(pb.get("distance", ""))
    except ValidationError:
        return None


def pbs_with_label(label: str, exclude: Path | None = None) -> list[dict]:
    """The personal bests for this distance. A PB is identified by its label ("5 km",
    "5_km" and "5 KM" are one distance), not by its file name, which may be older."""
    slug = pb_slug(label)
    return [p for p in load_all_pbs() if _label_slug(p) == slug and p["_path"] != exclude]


def free_pb_path(label: str, own: Path | None = None) -> Path:
    """5_km.json, or 5_km_2.json… if that name is taken by another file."""
    slug = pb_slug(label)
    path, n = child_path(PBS_DIR, f"{slug}.json"), 1
    while path.exists() and path != own:
        n += 1
        path = child_path(PBS_DIR, f"{slug}_{n}.json")
    return path


def superseded_history(current: dict, typed: list[dict]) -> list[dict]:
    """History for a PB that replaces `current`: current's history, current's own result
    and any lines typed in the form — without duplicates, newest first."""
    rows = list(current.get("previous_records", [])) + [{
        "time": current.get("total_time", ""),
        "date": current.get("date", ""),
        "location": current.get("location", ""),
    }] + typed
    seen, out = set(), []
    for r in rows:
        key = (r.get("time"), r.get("date"), r.get("location"))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return sorted(out, key=lambda r: r.get("date", ""), reverse=True)


def atomic_write_text(path: Path, text: str):
    """Write via a temp file in the same folder + os.replace: a crash or a full disk
    leaves the old file intact, never a truncated one. The temp name ends in .tmp, so
    load_all_*() can never mistake it for a record."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(10):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                # Windows refuses to replace a file that is open for reading, and the
                # background refresh reads data.js — retry through that short window.
                if attempt == 9:
                    raise
                time.sleep(0.05)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path: Path, record: dict):
    # allow_nan=False: NaN/Infinity are not JSON. The validators make this unreachable.
    atomic_write_text(path, json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False))


def remove_replaced(old_path: Path, new_path: Path) -> str:
    """Delete a renamed record's old file — call only after the new one is written.
    Returns a warning for the user if that fails (the record then exists twice)."""
    if old_path == new_path:
        return ""
    try:
        old_path.unlink(missing_ok=True)
        return ""
    except OSError as e:
        return (f"\n\nWarning: the old file {old_path.name} could not be removed ({e}). "
                "Delete it by hand, or the event will appear twice.")


def delete_record(path: Path, folder: Path):
    """Delete one record file — only ever a .json directly inside folder."""
    if path.suffix != ".json" or path.resolve().parent != folder.resolve():
        raise OSError(f"refusing to delete {path}: not a record in {folder}")
    path.unlink()


def _strip_meta(records):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]


def write_data_js() -> bool:
    """Rebuild data.js from the JSON files. Returns whether its content changed.

    Refuses (DataError) while any record file can't be loaded: rebuilding without it
    would silently drop that event from the site."""
    runs, run_problems = scan_records(RUNS_DIR, "run")
    pbs,  pb_problems  = scan_records(PBS_DIR, "pb")
    if run_problems or pb_problems:
        raise DataError("these files can't be loaded — fix or remove them first:\n  "
                        + "\n  ".join(run_problems + pb_problems))
    js   = (
        "// Auto-generated by add_new_event.py — do not edit manually\n"
        f"const RUNS_DATA = {json.dumps(_strip_meta(runs), ensure_ascii=False, indent=2)};\n\n"
        f"const PBS_DATA = {json.dumps(_strip_meta(pbs),  ensure_ascii=False, indent=2)};\n"
    )
    try:
        if DATA_JS.read_text("utf-8-sig") == js:
            return False
    except (OSError, UnicodeError):   # missing, unreadable or not UTF-8: just rewrite it
        pass
    atomic_write_text(DATA_JS, js)
    return True


def refresh_previews() -> str | None:
    """Regenerate the WebP previews the dashboard displays. Returns a problem, or None.

    Best-effort: ImageMagick is an external dependency, so a failure here must
    never take down the editor after the JSON has already been written.
    """
    try:
        import make_previews
        if make_previews.main([]) != 0:
            return "some photo previews failed — run make_previews.bat to see why"
    except Exception as exc:
        return f"photo previews not generated ({exc})"
    return None


def refresh_feed() -> str | None:
    """Regenerate atom.xml. Returns a problem, or None — like refresh_previews()."""
    try:
        import make_feed
        if make_feed.main([]) != 0:
            return "atom.xml not regenerated — run make_feed.bat to see why"
    except Exception as exc:
        return f"atom.xml not regenerated ({exc})"
    return None


def refresh_generated() -> list[str]:
    """Previews and atom.xml — both derived from data.js. Returns the problems."""
    problems = [refresh_previews(),   # data.js is the source of truth for which previews exist
                refresh_feed()]
    for p in problems:
        if p:
            print(f"Warning: {p}")
    return [p for p in problems if p]


class BackgroundRefresh:
    """Runs refresh_generated() off the Tk thread: encoding freshly added photos can take
    a while, and the window has to stay responsive meanwhile.

    One pass at a time; saves made while a pass runs are folded into one more pass,
    which reads the newest data.js. The problems the last finished pass reported are
    kept for the Tk thread to show (see App._poll_refresh).
    """

    def __init__(self, work=refresh_generated):
        self._work = work
        self._lock = threading.Lock()
        self._pending = False
        self._thread = None
        self._problems = []

    @property
    def problems(self) -> list[str]:
        with self._lock:
            return list(self._problems)

    def request(self):
        with self._lock:
            self._pending = True
            if self._thread is None:
                # Not a daemon: closing the window lets a pass in progress finish.
                self._thread = threading.Thread(target=self._loop, name="refresh-generated")
                self._thread.start()

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._thread is not None

    def _loop(self):
        while True:
            with self._lock:
                if not self._pending:
                    self._thread = None
                    return
                self._pending = False
            try:
                problems = [str(p) for p in (self._work() or [])]
            except Exception as exc:          # never leave a request unserved
                print(f"Warning: background refresh failed ({exc})")
                problems = [f"updating previews and atom.xml failed ({exc})"]
            with self._lock:
                self._problems = problems


# ── Medal and photos ─────────────────────────────────────────────────────────

def project_path(text: str) -> Path:
    """A path from the form. Stored paths (data/photos/...) are relative to the project,
    not to whatever directory the script happened to be started from."""
    p = Path(text.strip())
    return p if p.is_absolute() else BASE_DIR / p


def medal_source(text: str, current: str = "") -> Path | None:
    """The image to copy as the medal, or None to keep `current` (field empty or unchanged)."""
    s = text.strip()
    if not s or s == current:
        return None
    src = project_path(s)
    if not src.is_file():
        raise ValidationError(f"Medal photo: file not found — {s}")
    if src.suffix.lower() not in IMG_EXTS:
        raise ValidationError(f"Medal photo: {src.name} is not a supported image "
                              f"({', '.join(sorted(IMG_EXTS))}).")
    if current:
        cur = project_path(current)
        if cur.exists() and os.path.samefile(src, cur):
            return None                # the stored medal picked again via Browse…
    return src


def photos_source(text: str) -> Path | None:
    s = text.strip()
    if not s:
        return None
    src = project_path(s)
    if not src.is_dir():
        raise ValidationError(f"Photos folder: folder not found — {s}")
    return src


def _as_on_disk(path: Path) -> Path:
    """path spelled the way the file system stores it. Windows matches names without
    regard to case, but the site is served from a case-sensitive file system."""
    want = os.path.normcase(path.name)
    for entry in path.parent.iterdir():
        if os.path.normcase(entry.name) == want:
            return entry
    return path


def _stem_clash(target: Path) -> bool:
    """Another image in the folder with the same stem but a different extension
    (IMG_1.jpg next to IMG_1.png). Both would map to one preview, IMG_1.webp, and
    make_previews refuses to encode anything while such a pair exists."""
    name = os.path.normcase(target.name)
    stem = os.path.splitext(name)[0]
    return any(os.path.normcase(p.name) != name
               and os.path.splitext(os.path.normcase(p.name))[0] == stem
               and p.suffix.lower() in IMG_EXTS
               for p in target.parent.iterdir())


def place_file(src: Path, folder: Path, name: str) -> str:
    """Copy src into folder as name; return its data/... path.

    Never overwrites: if the name is taken by an identical file, that file is reused;
    otherwise the copy takes the next free name (IMG_1.jpg -> IMG_1_2.jpg). A name whose
    stem another image already uses is skipped too — see _stem_clash().
    """
    folder.mkdir(parents=True, exist_ok=True)
    stem, ext = os.path.splitext(name)
    target, n = folder / name, 1
    while target.exists() or _stem_clash(target):
        if target.is_file() and (os.path.samefile(src, target)
                                 or filecmp.cmp(src, target, shallow=False)):
            target = _as_on_disk(target)
            break
        n += 1
        target = folder / f"{stem}_{n}{ext}"
    else:
        shutil.copy2(src, target)
        # copy2 keeps the source's (often old) mtime, and make_previews trusts any
        # preview newer than its source — a leftover preview of a deleted photo with
        # this name would then be kept for the new one.
        os.utime(target)
    return target.relative_to(BASE_DIR).as_posix()


def copy_photos(src_folder: Path | None, event_key: str) -> list[str]:
    """Copy the images in src_folder to data/photos/<event_key>/; return their paths."""
    if src_folder is None:
        return []
    dest = child_path(PHOTOS_DIR, event_key)
    paths = [place_file(f, dest, f.name) for f in sorted(src_folder.iterdir())
             if f.is_file() and f.suffix.lower() in IMG_EXTS]
    return list(dict.fromkeys(paths))


def copy_medal(src: Path | None, event_key: str) -> str:
    """Copy the medal image to data/photos/<event_key>/medal.<ext>; return its path or ''."""
    if src is None:
        return ""
    return place_file(src, child_path(PHOTOS_DIR, event_key), "medal" + src.suffix.lower())


# ── Sneakers list ────────────────────────────────────────────────────────────

def load_sneakers() -> list:
    if SNEAKERS_FILE.exists():
        return json.loads(SNEAKERS_FILE.read_text("utf-8-sig"))
    return []


def save_sneakers(names: list):
    atomic_write_text(SNEAKERS_FILE, json.dumps(names, ensure_ascii=False, indent=2))


def ensure_sneaker(name: str):
    if not name:
        return
    names = load_sneakers()
    if name not in names:
        names.append(name)
        save_sneakers(names)


def remember_sneaker(name: str):
    """ensure_sneaker() after a save — the record is already written, so only warn."""
    try:
        ensure_sneaker(name)
    except (OSError, ValueError) as e:
        print(f"Warning: sneakers.json not updated ({e})")


def init_sneakers_file():
    if SNEAKERS_FILE.exists():
        return
    names = []
    for r in load_all_runs() + load_all_pbs():
        s = r.get("sneakers", "")
        if s and s not in names:
            names.append(s)
    save_sneakers(names)


# ── GUI ───────────────────────────────────────────────────────────────────────

PAD = {"padx": 8, "pady": 5}
ENTRY_W = 30


def labeled_entry(parent, label, row, default=""):
    tk.Label(parent, text=label, anchor="e", width=16).grid(row=row, column=0, sticky="e", **PAD)
    var = tk.StringVar(value=default)
    tk.Entry(parent, textvariable=var, width=ENTRY_W).grid(row=row, column=1, sticky="ew", **PAD)
    return var


def show_invalid(e):
    messagebox.showerror("Please check the form", str(e))


def show_failed(e):
    messagebox.showerror("Save failed", f"{e}\n\nNo existing record was changed.")


def confirm_same_day(run_date: str, others: list[dict]) -> bool:
    names = "\n".join(
        f"  • {r.get('race_name') or r.get('location') or '?'} — "
        f"{r.get('distance_km', '?')} km  ({r['_path'].name})" for r in others)
    return messagebox.askyesno(
        "Another run on this day",
        f"{run_date} already has:\n{names}\n\n"
        "Save this as an additional run on the same day? The existing run is not changed.")


def confirm_replace_pb(current: dict, new: dict) -> bool:
    msg = (f"There is already a personal best for \"{current.get('distance', '?')}\": "
           f"{current.get('total_time', '?')} on {current.get('date', '?')}.\n\n"
           f"Replace it with {new['total_time']} on {new['date']}? The old result moves into "
           "Previous records; its photos and medal are no longer shown (the files stay on disk).")
    try:
        if time_to_sec(new["total_time"]) >= time_to_sec(current.get("total_time", "")):
            msg += "\n\nNote: the new time is not faster than the current one."
    except (ValueError, IndexError):
        pass
    return messagebox.askyesno("Personal best already exists", msg)


class RunTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.columnconfigure(1, weight=1)

        today = date.today().isoformat()

        self.v_date        = labeled_entry(self, "Date (YYYY-MM-DD)", 0, today)
        self.v_race        = labeled_entry(self, "Race name", 1)
        self.v_location    = labeled_entry(self, "Location (EN)", 2)
        self.v_location_be = labeled_entry(self, "Location (BE)", 3)
        self.v_country     = labeled_entry(self, "Country (EN)", 4)
        self.v_country_be  = labeled_entry(self, "Country (BE)", 5)
        self.v_dist        = labeled_entry(self, "Distance (km)", 6)
        self.v_total_time  = labeled_entry(self, "Total time (H:MM:SS)", 7)
        self.v_hr_avg      = labeled_entry(self, "Avg HR (bpm)", 8)
        self.v_hr_max      = labeled_entry(self, "Max HR (bpm)", 9)
        self.v_elevation   = labeled_entry(self, "Elevation (m)", 10, "0")

        tk.Label(self, text="Sneakers", anchor="e", width=16).grid(row=11, column=0, sticky="e", **PAD)
        self.v_sneakers = tk.StringVar()
        self.cb_sneakers = ttk.Combobox(self, textvariable=self.v_sneakers, width=ENTRY_W - 2)
        self.cb_sneakers['values'] = load_sneakers()
        self.cb_sneakers.grid(row=11, column=1, sticky="ew", **PAD)

        self.v_video = labeled_entry(self, "Video link", 12)

        tk.Label(self, text="Medal photo", anchor="e", width=16).grid(row=13, column=0, sticky="e", **PAD)
        medal_frame = tk.Frame(self)
        medal_frame.grid(row=13, column=1, sticky="ew", **PAD)
        medal_frame.columnconfigure(0, weight=1)
        self.v_medal = tk.StringVar()
        tk.Entry(medal_frame, textvariable=self.v_medal).grid(row=0, column=0, sticky="ew")
        tk.Button(medal_frame, text="Browse…", command=self._browse_medal).grid(row=0, column=1, padx=(6, 0))

        # Photos folder row
        tk.Label(self, text="Photos folder", anchor="e", width=16).grid(row=14, column=0, sticky="e", **PAD)
        ph_frame = tk.Frame(self)
        ph_frame.grid(row=14, column=1, sticky="ew", **PAD)
        ph_frame.columnconfigure(0, weight=1)
        self.v_photos = tk.StringVar()
        tk.Entry(ph_frame, textvariable=self.v_photos).grid(row=0, column=0, sticky="ew")
        tk.Button(ph_frame, text="Browse…", command=self._browse).grid(row=0, column=1, padx=(6, 0))

        tk.Button(self, text="💾  Save Run", command=self._save,
                  bg="#e8521b", fg="white", font=("", 11, "bold"),
                  padx=18, pady=6).grid(row=15, column=0, columnspan=2, pady=16)

    def _browse(self):
        folder = filedialog.askdirectory(title="Select photos folder")
        if folder:
            self.v_photos.set(folder)

    def _browse_medal(self):
        path = filedialog.askopenfilename(title="Select medal photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif")])
        if path:
            self.v_medal.set(path)

    def _save(self):
        try:
            chk = Checker()
            run = validate_run(run_form(self), chk)
            medal = chk(medal_source, self.v_medal.get())
            photos = chk(photos_source, self.v_photos.get())
            chk.raise_if_any()

            path, others = run_target(run["date"])
            if others and not confirm_same_day(run["date"], others):
                return
            rid = new_run_id(run["date"])
            if rid != run["date"]:            # only stored when the date alone isn't unique
                run = {"id": rid, **run}
            run["medal"]  = copy_medal(medal, path.stem)
            run["photos"] = copy_photos(photos, path.stem)
            write_json(path, run)
        except ValidationError as e:
            return show_invalid(e)
        except (OSError, ValueError) as e:
            return show_failed(e)

        remember_sneaker(run["sneakers"])
        self.app.saved("Saved", f"Run on {run['date']} saved as {path.name}.\n"
                                f"{len(run['photos'])} photo(s) copied.")


class PBTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.columnconfigure(1, weight=1)

        today = date.today().isoformat()

        self.v_distance    = labeled_entry(self, "Distance label", 0, "5 km")
        self.v_distance_km = labeled_entry(self, "Distance (km)", 1)
        self.v_total_time  = labeled_entry(self, "Total time (H:MM:SS)", 2)
        self.v_date        = labeled_entry(self, "Date (YYYY-MM-DD)", 3, today)
        self.v_race        = labeled_entry(self, "Race name", 4)
        self.v_location    = labeled_entry(self, "Location (EN)", 5)
        self.v_location_be = labeled_entry(self, "Location (BE)", 6)
        self.v_country     = labeled_entry(self, "Country (EN)", 7)
        self.v_country_be  = labeled_entry(self, "Country (BE)", 8)
        self.v_hr_avg      = labeled_entry(self, "Avg HR (bpm)", 9)
        self.v_hr_max      = labeled_entry(self, "Max HR (bpm)", 10)

        tk.Label(self, text="Sneakers", anchor="e", width=16).grid(row=11, column=0, sticky="e", **PAD)
        self.v_sneakers = tk.StringVar()
        self.cb_sneakers = ttk.Combobox(self, textvariable=self.v_sneakers, width=ENTRY_W - 2)
        self.cb_sneakers['values'] = load_sneakers()
        self.cb_sneakers.grid(row=11, column=1, sticky="ew", **PAD)

        self.v_video = labeled_entry(self, "Video link", 12)

        tk.Label(self, text="Medal photo", anchor="e", width=16).grid(row=13, column=0, sticky="e", **PAD)
        medal_frame = tk.Frame(self)
        medal_frame.grid(row=13, column=1, sticky="ew", **PAD)
        medal_frame.columnconfigure(0, weight=1)
        self.v_medal = tk.StringVar()
        tk.Entry(medal_frame, textvariable=self.v_medal).grid(row=0, column=0, sticky="ew")
        tk.Button(medal_frame, text="Browse…", command=self._browse_medal).grid(row=0, column=1, padx=(6, 0))

        tk.Label(self, text="Photos folder", anchor="e", width=16).grid(row=14, column=0, sticky="e", **PAD)
        ph_frame = tk.Frame(self)
        ph_frame.grid(row=14, column=1, sticky="ew", **PAD)
        ph_frame.columnconfigure(0, weight=1)
        self.v_photos = tk.StringVar()
        tk.Entry(ph_frame, textvariable=self.v_photos).grid(row=0, column=0, sticky="ew")
        tk.Button(ph_frame, text="Browse…", command=self._browse).grid(row=0, column=1, padx=(6, 0))

        tk.Label(self, text="Previous records", anchor="e", width=16).grid(row=15, column=0, sticky="ne", **PAD)
        self.prev_text = tk.Text(self, height=4, width=ENTRY_W)
        self.prev_text.grid(row=15, column=1, sticky="ew", **PAD)
        tk.Label(self, text="Format: time|date|location\none per line",
                 fg="grey", font=("", 8)).grid(row=16, column=1, sticky="w", padx=8)

        tk.Button(self, text="💾  Save Personal Best", command=self._save,
                  bg="#e8521b", fg="white", font=("", 11, "bold"),
                  padx=18, pady=6).grid(row=17, column=0, columnspan=2, pady=16)

    def _browse(self):
        folder = filedialog.askdirectory(title="Select photos folder")
        if folder:
            self.v_photos.set(folder)

    def _browse_medal(self):
        path = filedialog.askopenfilename(title="Select medal photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif")])
        if path:
            self.v_medal.set(path)

    def _save(self):
        try:
            chk = Checker()
            pb = validate_pb(pb_form(self), chk)
            medal = chk(medal_source, self.v_medal.get())
            photos = chk(photos_source, self.v_photos.get())
            chk.raise_if_any()

            matches = pbs_with_label(pb["distance"])
            if len(matches) > 1:
                raise ValidationError(
                    f'Distance label: several personal bests already use "{pb["distance"]}" ('
                    + ", ".join(m["_path"].name for m in matches)
                    + "). Delete the extra ones in Edit Personal Best first.")
            if matches:
                # A new best for a distance that already has one: an explicit update
                # that keeps the old result in the history, never a silent overwrite.
                current = matches[0]
                if not confirm_replace_pb(current, pb):
                    return
                pb["previous_records"] = superseded_history(current, pb["previous_records"])
                path = current["_path"]          # whatever that file happens to be called
            else:
                path = free_pb_path(pb["distance"])
            key = "pb_" + path.stem
            pb["medal"]  = copy_medal(medal, key)
            pb["photos"] = copy_photos(photos, key)
            write_json(path, pb)
        except ValidationError as e:
            return show_invalid(e)
        except (OSError, ValueError) as e:
            return show_failed(e)

        remember_sneaker(pb["sneakers"])
        self.app.saved("Saved", f"Personal Best '{pb['distance']}' saved.\n"
                                f"{len(pb['photos'])} photo(s) copied.")


class EditRunTab(tk.Frame):
    """Select an existing run to edit or delete."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.runs = []
        self.selected_index = None
        self.columnconfigure(1, weight=1)

        # ── Listbox ──────────────────────────────────────────────
        tk.Label(self, text="Select run:", font=("", 9, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))

        list_frame = tk.Frame(self)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(list_frame, height=5, font=("Courier", 9), exportselection=False)
        sb = tk.Scrollbar(list_frame, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.grid(row=0, column=0, sticky="ew")
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # ── Fields ───────────────────────────────────────────────
        self.v_date        = labeled_entry(self, "Date (YYYY-MM-DD)", 2)
        self.v_race        = labeled_entry(self, "Race name", 3)
        self.v_location    = labeled_entry(self, "Location (EN)", 4)
        self.v_location_be = labeled_entry(self, "Location (BE)", 5)
        self.v_country     = labeled_entry(self, "Country (EN)", 6)
        self.v_country_be  = labeled_entry(self, "Country (BE)", 7)
        self.v_dist        = labeled_entry(self, "Distance (km)", 8)
        self.v_total_time  = labeled_entry(self, "Total time (H:MM:SS)", 9)
        self.v_hr_avg      = labeled_entry(self, "Avg HR (bpm)", 10)
        self.v_hr_max      = labeled_entry(self, "Max HR (bpm)", 11)
        self.v_elevation   = labeled_entry(self, "Elevation (m)", 12)

        tk.Label(self, text="Sneakers", anchor="e", width=16).grid(row=13, column=0, sticky="e", **PAD)
        self.v_sneakers = tk.StringVar()
        self.cb_sneakers = ttk.Combobox(self, textvariable=self.v_sneakers, width=ENTRY_W - 2)
        self.cb_sneakers['values'] = load_sneakers()
        self.cb_sneakers.grid(row=13, column=1, sticky="ew", **PAD)

        self.v_video = labeled_entry(self, "Video link", 14)

        tk.Label(self, text="Medal photo", anchor="e", width=16).grid(row=15, column=0, sticky="e", **PAD)
        medal_frame = tk.Frame(self)
        medal_frame.grid(row=15, column=1, sticky="ew", **PAD)
        medal_frame.columnconfigure(0, weight=1)
        self.v_medal = tk.StringVar()
        tk.Entry(medal_frame, textvariable=self.v_medal).grid(row=0, column=0, sticky="ew")
        tk.Button(medal_frame, text="Browse…", command=self._browse_medal).grid(row=0, column=1, padx=(6, 0))

        tk.Label(self, text="Add photos folder", anchor="e", width=16).grid(row=16, column=0, sticky="e", **PAD)
        ph_frame = tk.Frame(self)
        ph_frame.grid(row=16, column=1, sticky="ew", **PAD)
        ph_frame.columnconfigure(0, weight=1)
        self.v_photos = tk.StringVar()
        tk.Entry(ph_frame, textvariable=self.v_photos).grid(row=0, column=0, sticky="ew")
        tk.Button(ph_frame, text="Browse…", command=self._browse).grid(row=0, column=1, padx=(6, 0))

        tk.Label(self, text="(leave blank to keep\nexisting photos)",
                 fg="grey", font=("", 8)).grid(row=17, column=1, sticky="w", padx=8)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=18, column=0, columnspan=2, pady=14)
        tk.Button(btn_frame, text="💾  Save Changes", command=self._save,
                  bg="#e8521b", fg="white", font=("", 11, "bold"),
                  padx=14, pady=6).pack(side="left", padx=6)
        tk.Button(btn_frame, text="🗑  Delete Run", command=self._delete,
                  bg="#c0392b", fg="white", font=("", 11, "bold"),
                  padx=14, pady=6).pack(side="left", padx=6)

        self.refresh()

    def refresh(self):
        self.runs = sorted(load_all_runs(), key=lambda x: x["date"], reverse=True)
        self.listbox.delete(0, "end")
        for r in self.runs:
            self.listbox.insert("end", f"{r['date']}  {r.get('location', '')}  {r['distance_km']} km")
        self.selected_index = None
        self._clear_fields()

    def _clear_fields(self):
        for v in (self.v_date, self.v_race, self.v_location, self.v_location_be,
                  self.v_country, self.v_country_be, self.v_dist, self.v_total_time,
                  self.v_hr_avg, self.v_hr_max, self.v_elevation, self.v_sneakers, self.v_video,
                  self.v_medal, self.v_photos):
            v.set("")

    def _on_select(self, _event):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.selected_index = sel[0]
        r = self.runs[self.selected_index]
        self.v_date.set(r.get("date", ""))
        self.v_race.set(r.get("race_name", ""))
        self.v_location.set(r.get("location", ""))
        self.v_location_be.set(r.get("location_be", ""))
        self.v_country.set(r.get("country", ""))
        self.v_country_be.set(r.get("country_be", ""))
        self.v_dist.set(str(r.get("distance_km", "")))
        self.v_total_time.set(r.get("total_time", ""))
        self.v_hr_avg.set(number_text(r.get("hr_avg", "")))
        self.v_hr_max.set(number_text(r.get("hr_max", "")))
        self.v_elevation.set(number_text(r.get("elevation", 0)))
        self.v_sneakers.set(r.get("sneakers", ""))
        self.v_video.set(r.get("video", ""))
        self.v_medal.set(r.get("medal", ""))
        self.v_photos.set("")

    def _browse(self):
        folder = filedialog.askdirectory(title="Select photos folder")
        if folder:
            self.v_photos.set(folder)

    def _browse_medal(self):
        path = filedialog.askopenfilename(title="Select medal photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif")])
        if path:
            self.v_medal.set(path)

    def _save(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a run from the list first.")
            return
        old = self.runs[self.selected_index]
        try:
            chk = Checker()
            fields = validate_run(run_form(self), chk)
            medal = chk(medal_source, self.v_medal.get(), old.get("medal", ""))
            photos = chk(photos_source, self.v_photos.get())
            chk.raise_if_any()

            path, others = run_target(fields["date"], old)
            if others and not confirm_same_day(fields["date"], others):
                return
            run = {k: v for k, v in old.items() if not k.startswith("_")}   # keeps unknown keys
            if fields["date"] != old.get("date") and "id" not in run:
                # The feed id was the old date; keep it, so feed readers see this entry
                # as updated rather than as a new race.
                run = {"id": published_ids().get(old["_path"], old["date"]), **run}
            run.update(fields)
            run["medal"]  = copy_medal(medal, path.stem) if medal else old.get("medal", "")
            run["photos"] = list(dict.fromkeys(old.get("photos", []) + copy_photos(photos, path.stem)))
            write_json(path, run)
        except ValidationError as e:
            return show_invalid(e)
        except (OSError, ValueError) as e:
            return show_failed(e)

        warning = remove_replaced(old["_path"], path)
        remember_sneaker(run["sneakers"])
        self.app.saved("Saved", f"Run on {run['date']} updated." + warning)

    def _delete(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a run from the list first.")
            return
        run = self.runs[self.selected_index]
        if not messagebox.askyesno("Confirm delete",
                                   f"Delete run {run['date']} – "
                                   f"{run.get('location') or run.get('race_name') or run['_path'].name}?\n"
                                   "This cannot be undone."):
            return
        path = run["_path"]
        try:
            delete_record(path, RUNS_DIR)
            message = f"Run {run['date']} deleted ({path.name})."
        except FileNotFoundError:
            message = f"{path.name} had already been removed."
        except OSError as e:
            messagebox.showerror("Delete failed", f"{path.name} could not be deleted:\n{e}")
            return
        self.app.saved("Deleted", message)


class EditPBTab(tk.Frame):
    """Select an existing personal best to edit or delete."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.pbs = []
        self.selected_index = None
        self.columnconfigure(1, weight=1)

        tk.Label(self, text="Select personal best:", font=("", 9, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))

        list_frame = tk.Frame(self)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(list_frame, height=4, font=("Courier", 9), exportselection=False)
        sb = tk.Scrollbar(list_frame, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.grid(row=0, column=0, sticky="ew")
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.v_distance    = labeled_entry(self, "Distance label", 2)
        self.v_distance_km = labeled_entry(self, "Distance (km)", 3)
        self.v_total_time  = labeled_entry(self, "Total time (H:MM:SS)", 4)
        self.v_date        = labeled_entry(self, "Date (YYYY-MM-DD)", 5)
        self.v_race        = labeled_entry(self, "Race name", 6)
        self.v_location    = labeled_entry(self, "Location (EN)", 7)
        self.v_location_be = labeled_entry(self, "Location (BE)", 8)
        self.v_country     = labeled_entry(self, "Country (EN)", 9)
        self.v_country_be  = labeled_entry(self, "Country (BE)", 10)
        self.v_hr_avg      = labeled_entry(self, "Avg HR (bpm)", 11)
        self.v_hr_max      = labeled_entry(self, "Max HR (bpm)", 12)

        tk.Label(self, text="Sneakers", anchor="e", width=16).grid(row=13, column=0, sticky="e", **PAD)
        self.v_sneakers = tk.StringVar()
        self.cb_sneakers = ttk.Combobox(self, textvariable=self.v_sneakers, width=ENTRY_W - 2)
        self.cb_sneakers['values'] = load_sneakers()
        self.cb_sneakers.grid(row=13, column=1, sticky="ew", **PAD)

        self.v_video = labeled_entry(self, "Video link", 14)

        tk.Label(self, text="Medal photo", anchor="e", width=16).grid(row=15, column=0, sticky="e", **PAD)
        medal_frame = tk.Frame(self)
        medal_frame.grid(row=15, column=1, sticky="ew", **PAD)
        medal_frame.columnconfigure(0, weight=1)
        self.v_medal = tk.StringVar()
        tk.Entry(medal_frame, textvariable=self.v_medal).grid(row=0, column=0, sticky="ew")
        tk.Button(medal_frame, text="Browse…", command=self._browse_medal).grid(row=0, column=1, padx=(6, 0))

        tk.Label(self, text="Add photos folder", anchor="e", width=16).grid(row=16, column=0, sticky="e", **PAD)
        ph_frame = tk.Frame(self)
        ph_frame.grid(row=16, column=1, sticky="ew", **PAD)
        ph_frame.columnconfigure(0, weight=1)
        self.v_photos = tk.StringVar()
        tk.Entry(ph_frame, textvariable=self.v_photos).grid(row=0, column=0, sticky="ew")
        tk.Button(ph_frame, text="Browse…", command=self._browse).grid(row=0, column=1, padx=(6, 0))

        tk.Label(self, text="Previous records", anchor="e", width=16).grid(row=17, column=0, sticky="ne", **PAD)
        self.prev_text = tk.Text(self, height=4, width=ENTRY_W)
        self.prev_text.grid(row=17, column=1, sticky="ew", **PAD)
        tk.Label(self, text="Format: time|date|location\none per line",
                 fg="grey", font=("", 8)).grid(row=18, column=1, sticky="w", padx=8)

        btn_frame = tk.Frame(self)
        btn_frame.grid(row=19, column=0, columnspan=2, pady=14)
        tk.Button(btn_frame, text="💾  Save Changes", command=self._save,
                  bg="#e8521b", fg="white", font=("", 11, "bold"),
                  padx=14, pady=6).pack(side="left", padx=6)
        tk.Button(btn_frame, text="🗑  Delete PB", command=self._delete,
                  bg="#c0392b", fg="white", font=("", 11, "bold"),
                  padx=14, pady=6).pack(side="left", padx=6)

        self.refresh()

    def refresh(self):
        self.pbs = load_all_pbs()
        self.listbox.delete(0, "end")
        for pb in self.pbs:
            self.listbox.insert("end", f"{pb['distance']}  {pb['total_time']}  {pb['date']}")
        self.selected_index = None
        self._clear_fields()

    def _clear_fields(self):
        for v in (self.v_distance, self.v_distance_km, self.v_total_time, self.v_date,
                  self.v_race, self.v_location, self.v_location_be, self.v_country,
                  self.v_country_be, self.v_hr_avg, self.v_hr_max,
                  self.v_sneakers, self.v_video, self.v_medal, self.v_photos):
            v.set("")
        self.prev_text.delete("1.0", "end")

    def _on_select(self, _event):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.selected_index = sel[0]
        pb = self.pbs[self.selected_index]
        self.v_distance.set(pb.get("distance", ""))
        self.v_distance_km.set(str(pb.get("distance_km", "")))
        self.v_total_time.set(pb.get("total_time", ""))
        self.v_date.set(pb.get("date", ""))
        self.v_race.set(pb.get("race_name", ""))
        self.v_location.set(pb.get("location", ""))
        self.v_location_be.set(pb.get("location_be", ""))
        self.v_country.set(pb.get("country", ""))
        self.v_country_be.set(pb.get("country_be", ""))
        self.v_hr_avg.set(number_text(pb.get("hr_avg", "")))
        self.v_hr_max.set(number_text(pb.get("hr_max", "")))
        self.v_sneakers.set(pb.get("sneakers", ""))
        self.v_video.set(pb.get("video", ""))
        self.v_medal.set(pb.get("medal", ""))
        self.v_photos.set("")
        self.prev_text.delete("1.0", "end")
        for r in pb.get("previous_records", []):
            self.prev_text.insert(
                "end", f"{r.get('time', '')}|{r.get('date', '')}|{r.get('location', '')}\n")

    def _browse(self):
        folder = filedialog.askdirectory(title="Select photos folder")
        if folder:
            self.v_photos.set(folder)

    def _browse_medal(self):
        path = filedialog.askopenfilename(title="Select medal photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif")])
        if path:
            self.v_medal.set(path)

    def _save(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a personal best from the list first.")
            return
        old = self.pbs[self.selected_index]
        try:
            chk = Checker()
            fields = validate_pb(pb_form(self), chk)
            medal = chk(medal_source, self.v_medal.get(), old.get("medal", ""))
            photos = chk(photos_source, self.v_photos.get())
            chk.raise_if_any()

            # Same distance -> same file, whatever its name. Another distance must not
            # be one that already has a PB: that would leave two for one distance.
            own = old["_path"]
            if pb_slug(fields["distance"]) == _label_slug(old):
                path = own
            else:
                taken = pbs_with_label(fields["distance"], exclude=own)
                if taken:
                    raise ValidationError(
                        f'Distance label: "{fields["distance"]}" already has a personal best '
                        f"({taken[0]['_path'].name}). Edit or delete that one instead of "
                        "renaming this one onto it.")
                path = free_pb_path(fields["distance"], own)
            key = "pb_" + path.stem
            pb = {k: v for k, v in old.items() if not k.startswith("_")}    # keeps unknown keys
            pb.update(fields)
            pb["medal"]  = copy_medal(medal, key) if medal else old.get("medal", "")
            pb["photos"] = list(dict.fromkeys(old.get("photos", []) + copy_photos(photos, key)))
            write_json(path, pb)
        except ValidationError as e:
            return show_invalid(e)
        except (OSError, ValueError) as e:
            return show_failed(e)

        warning = remove_replaced(old["_path"], path)
        remember_sneaker(pb["sneakers"])
        self.app.saved("Saved", f"Personal Best '{pb['distance']}' updated." + warning)

    def _delete(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a personal best from the list first.")
            return
        pb = self.pbs[self.selected_index]
        if not messagebox.askyesno("Confirm delete",
                                   f"Delete PB '{pb['distance']}' ({pb['total_time']})?\n"
                                   "This cannot be undone."):
            return
        path = pb["_path"]
        try:
            delete_record(path, PBS_DIR)
            message = f"Personal Best '{pb['distance']}' deleted ({path.name})."
        except FileNotFoundError:
            message = f"{path.name} had already been removed."
        except OSError as e:
            messagebox.showerror("Delete failed", f"{path.name} could not be deleted:\n{e}")
            return
        self.app.saved("Deleted", message)


class ViewTab(tk.Frame):
    """Simple read-only list of existing events."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        tk.Label(self, text="Existing events (read-only)", font=("", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        self.text = tk.Text(self, state="disabled", wrap="none", font=("Courier", 9))
        sb = tk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=4)
        sb.grid(row=1, column=1, sticky="ns", pady=4)

        tk.Button(self, text="↺  Refresh", command=self.refresh).grid(
            row=2, column=0, columnspan=2, pady=8)

        self.refresh()

    def refresh(self):
        lines = ["═══ RUNS ═══"]
        for r in sorted(load_all_runs(), key=lambda x: x["date"], reverse=True):
            lines.append(f"  {r['date']}  {r.get('location', '')}  {r['distance_km']} km  {r['total_time']}")
        lines += ["", "═══ PERSONAL BESTS ═══"]
        for pb in load_all_pbs():
            lines.append(f"  {pb['distance']}  {pb['total_time']}  {pb['date']}  {pb.get('location', '')}")
        problems = load_problems()
        if problems:
            lines += ["", "═══ SKIPPED FILES (not shown above) ═══"] + [f"  {p}" for p in problems]
        content = "\n".join(lines)

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Running Log – Event Manager")
        self.resizable(True, True)
        self.minsize(520, 520)

        self.refresher = BackgroundRefresh()
        self._polling = False

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Status line: background progress, or what the last preview/feed pass failed at.
        bar = tk.Frame(self)
        bar.pack(fill="x", padx=12, pady=(2, 6))
        self.status = tk.StringVar()
        self.status_label = tk.Label(bar, textvariable=self.status, fg="grey", anchor="w",
                                     justify="left", wraplength=460)
        self.status_label.pack(side="left", fill="x", expand=True)
        self.retry_button = tk.Button(bar, text="Retry", command=self.start_refresh)

        self.run_tab      = RunTab(nb, self)
        self.pb_tab       = PBTab(nb, self)
        self.edit_run_tab = EditRunTab(nb, self)
        self.edit_pb_tab  = EditPBTab(nb, self)
        self.view_tab     = ViewTab(nb, self)

        nb.add(self.run_tab,      text="  Add Run  ")
        nb.add(self.pb_tab,       text="  Add Personal Best  ")
        nb.add(self.edit_run_tab, text="  Edit Run  ")
        nb.add(self.edit_pb_tab,  text="  Edit Personal Best  ")
        nb.add(self.view_tab,     text="  View All  ")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Files that can't be loaded are left out of the lists (instead of crashing a tab)
        # and block data.js rebuilds until fixed — say which and why.
        problems = load_problems()
        if problems:
            shown = problems[:12] + ([f"… and {len(problems) - 12} more"] if len(problems) > 12 else [])
            messagebox.showwarning(
                "Some files were skipped",
                "These files can't be loaded, so they are not shown in the editor, and "
                "data/data.js is not rebuilt until they are fixed or removed (rebuilding "
                "without them would drop them from the site):\n\n" + "\n".join(shown))

        # Catch up on anything the last session left undone: JSON files data.js doesn't
        # reflect yet (a save whose rebuild failed, files edited by hand) and a preview /
        # feed pass that was cut short. A pass with nothing to do takes a few hundredths
        # of a second, so it always runs.
        if not problems:           # ids are only decidable with every run loaded
            try:
                for name in freeze_feed_ids():
                    print(f"Stored the published feed id in {name}")
            except (OSError, ValueError) as e:
                print(f"Warning: feed ids not checked ({e})")
        try:
            write_data_js()
        except (OSError, ValueError) as e:
            print(f"Warning: data/data.js not rebuilt ({e})")
        self.start_refresh()

    def start_refresh(self):
        self.refresher.request()
        if not self._polling:
            self._poll_refresh()

    def saved(self, title, message):
        """Common tail of every save and delete: data.js, then report, then refresh."""
        while True:
            try:
                write_data_js()
                break
            except (OSError, ValueError) as e:
                # Never suggest saving again: the record is written, and a second save
                # would add a duplicate same-day run or fold a PB into its own history.
                if not messagebox.askretrycancel(
                        "data.js not updated",
                        f"{message}\n\nThe record itself is saved, but data/data.js could not "
                        f"be rebuilt ({e}), so the site does not show the change yet.\n\n"
                        "Retry now? Otherwise it is rebuilt after the next save or delete, "
                        "or when the editor is started again."):
                    self.refresh_lists()
                    return
        self.start_refresh()
        messagebox.showinfo(title, message)
        self.refresh_lists()

    def _poll_refresh(self):
        busy = self.refresher.busy
        self._polling = busy
        if busy:
            self._set_status("Updating photo previews and atom.xml…")
            self.after(300, self._poll_refresh)
        else:
            problems = self.refresher.problems      # read here, on the Tk thread
            self._set_status("⚠ " + "; ".join(problems) if problems else "", warn=bool(problems))

    def _set_status(self, text, warn=False):
        self.status.set(text)
        self.status_label.configure(fg="#b3261e" if warn else "grey")
        if warn:
            self.retry_button.pack(side="right", padx=(6, 0))
        else:
            self.retry_button.pack_forget()

    def _on_close(self):
        """Leave mainloop only after the background pass is done. Exiting while it runs
        shuts down the thread pool make_previews uses (a queued pass then skips its
        previews), and lets Tk objects be garbage-collected on a worker thread, which
        aborts the process. So hide the window and wait."""
        if self.refresher.busy:
            if self.state() != "withdrawn":
                self.withdraw()
                print("Finishing photo previews and atom.xml before exiting…")
            self.after(200, self._on_close)
        else:
            self.destroy()

    def refresh_lists(self):
        try:
            names = load_sneakers()
        except (OSError, ValueError):
            names = None
        if names is not None:
            for tab in (self.run_tab, self.pb_tab, self.edit_run_tab, self.edit_pb_tab):
                tab.cb_sneakers['values'] = names
        self.edit_run_tab.refresh()
        self.edit_pb_tab.refresh()
        self.view_tab.refresh()


if __name__ == "__main__":
    init_sneakers_file()
    app = App()      # keep a reference: the widgets are then freed at exit, on this thread
    app.mainloop()
