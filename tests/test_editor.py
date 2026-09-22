"""
Regression tests for add_new_event.py (and the make_feed.py / make_previews.py parts it
drives).

Everything runs on a throw-away copy of the scripts in a temp folder, with its own small
set of runs and personal bests, so the real data/ folder is never touched. One check
also copies the real data/runs and data/pbs there and makes sure every record opens and
saves back byte-for-byte unchanged.

    python tests/test_editor.py
    python tests/test_editor.py --require-gui     # fail, rather than skip, without Tk

The checks of validation, record loading, file naming, feed ids and the feed/preview
files need no GUI and always run. The rest drive the real Tk forms; without a usable
Tk/Tcl they are reported as skipped. ImageMagick ("magick" on PATH) is optional: without
it the checks that encode real previews are skipped.
"""

import contextlib
import gc
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Child Pythons write UTF-8 and are read as UTF-8, whatever this machine's code page is
# (GitHub's Windows runners pipe output as cp1252, where Cyrillic can't be encoded).
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
sys.stdout.reconfigure(errors="backslashreplace")     # our own prints never crash on it
REQUIRE_GUI = "--require-gui" in sys.argv
SCRIPTS = ("add_new_event.py", "make_previews.py", "make_feed.py")
HAS_MAGICK = shutil.which("magick") is not None
TMP = Path(tempfile.mkdtemp(prefix="running_log_tests_"))
SANDBOX = TMP / "project"


# ── Fixture: a small log with the awkward cases of the real one ────────────────
# Fractional track times, Cyrillic PB labels, medals, photos, PB history.

def _run(date, **kw):
    rec = {"date": date, "race_name": f"Race {date}", "location": "Batumi", "location_be": "Батумі",
           "country": "Georgia", "country_be": "Грузія", "distance_km": 10.0, "total_time": "0:45:00",
           "hr_avg": 150, "hr_max": 170, "elevation": 0, "sneakers": "Shoe A", "video": "",
           "medal": "", "photos": []}
    rec.update(kw)
    return rec


def _pb(label, km, time_, date, history=()):
    return {"distance": label, "distance_km": km, "total_time": time_, "date": date,
            "race_name": f"PB {label}", "location": "Batumi", "location_be": "Батумі",
            "country": "Georgia", "country_be": "Грузія", "hr_avg": 160, "hr_max": 180,
            "sneakers": "Shoe B", "video": "", "medal": "", "photos": [],
            "previous_records": [{"time": t, "date": d, "location": loc} for t, d, loc in history]}


RUNS = {
    "2024-05-26": _run("2024-05-26", distance_km=21.1, total_time="1:40:08",
                       medal="data/photos/2024-05-26/medal.jpg"),
    "2024-06-08": _run("2024-06-08", medal="data/photos/2024-06-08/medal.jpg",
                       photos=["data/photos/2024-06-08/IMG_1.jpg", "data/photos/2024-06-08/IMG_2.jpg"]),
    "2024-06-16": _run("2024-06-16", medal="data/photos/2024-06-16/medal.jpg"),
    "2024-12-21": _run("2024-12-21", total_time="10:00:00", distance_km=100.0),
    "2025-01-25": _run("2025-01-25"),
    "2025-08-09": _run("2025-08-09", distance_km=0.2, total_time="0:00:27.4"),
    "2025-09-13": _run("2025-09-13"),
    "2025-11-22": _run("2025-11-22", distance_km=3.0, total_time="0:11:43.18",
                       photos=["data/photos/2025-11-22/IMG_9.jpg"]),
}
PBS = {
    "10_km": _pb("10 km", 10.0, "0:40:05", "2026-04-18",
                 [("40:58", "2024-05-04", "Батумі"), ("41:15", "2023-05-16", "Батумі")]),
    "200_m": _pb("200 m", 0.2, "0:00:27.40", "2025-08-09"),
    "3_km": _pb("3 km", 3.0, "0:11:43.18", "2025-11-21"),
    "5_км": _pb("5 км", 5.0, "0:19:14", "2026-05-31",
                [("19:36", "2024-04-27", "Батумі"), ("20:21", "2023-05-16", "Тбілісі")]),
    "21.1_км": _pb("21.1 км", 21.1, "1:40:08", "2024-09-22"),
}


def fake_image(path: Path, payload: bytes) -> Path:
    """Content only matters for byte comparisons, so this needn't be a decodable JPEG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff" + payload)
    return path


def build_project(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    for f in SCRIPTS:
        shutil.copy2(REPO / f, root / f)
    for d in ("runs", "pbs", "photos"):
        (root / "data" / d).mkdir(parents=True, exist_ok=True)
    for stem, rec in RUNS.items():
        (root / "data/runs" / f"{stem}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), "utf-8")
        for p in [rec["medal"]] * bool(rec["medal"]) + rec["photos"]:
            fake_image(root / p, p.encode())
    for stem, rec in PBS.items():
        (root / "data/pbs" / f"{stem}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), "utf-8")
    (root / "data/sneakers.json").write_text('["Shoe A", "Shoe B"]', "utf-8")


build_project(SANDBOX)
sys.path.insert(0, str(SANDBOX))
os.chdir(SANDBOX)
a = importlib.import_module("add_new_event")
mf = importlib.import_module("make_feed")
mp = importlib.import_module("make_previews")
assert a.BASE_DIR == SANDBOX.resolve(), a.BASE_DIR
a.write_data_js()

# ── Dialog stubs: record what would have been shown, answer from ANSWER/RETRY ──
LOG = []
ANSWER = {"yes": True}
RETRY = {"yes": False}     # never True for long: App.saved() retries for as long as it is
mb = a.messagebox
mb.showinfo    = lambda t, m, **k: LOG.append(("info", t, m))
mb.showerror   = lambda t, m, **k: LOG.append(("error", t, m))
mb.showwarning = lambda t, m, **k: LOG.append(("warn", t, m))
mb.askyesno    = lambda t, m, **k: (LOG.append(("ask", t, m)), ANSWER["yes"])[1]
mb.askretrycancel = lambda t, m, **k: (LOG.append(("retry", t, m)), RETRY["yes"])[1]

# The background pass only records that it was asked for; the preview/feed code is
# exercised directly where it matters.
REFRESHES = []
a.BackgroundRefresh.__init__.__defaults__ = (lambda: REFRESHES.append(1),)
try:
    app = a.App()
    app.withdraw()
    NO_TK = ""
except a.tk.TclError as e:          # no usable Tcl/Tk: run everything that needs no GUI
    app, NO_TK = None, str(e)

RESULTS, SKIPPED = [], []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


def last(kind=None):
    for e in reversed(LOG):
        if kind is None or e[0] == kind:
            return e
    return None


def snapshot():
    return {f"{d}/{f.name}": f.read_bytes()
            for d in ("runs", "pbs") for f in sorted((SANDBOX / "data" / d).iterdir())}


def photos_snapshot():
    root = SANDBOX / "data/photos"
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def src_dir(name):
    d = TMP / "src" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def rjson(rel):
    return json.loads((SANDBOX / rel).read_text("utf-8"))


def select_run(stem):
    t = app.edit_run_tab
    t.refresh()
    idx = next(i for i, r in enumerate(t.runs) if r["_path"].stem == stem)
    t.listbox.selection_clear(0, "end")
    t.listbox.selection_set(idx)
    t._on_select(None)
    return t


def select_pb(stem):
    t = app.edit_pb_tab
    t.refresh()
    idx = next(i for i, r in enumerate(t.pbs) if r["_path"].stem == stem)
    t.listbox.selection_clear(0, "end")
    t.listbox.selection_set(idx)
    t._on_select(None)
    return t


def fill_run(t, **kw):
    base = dict(date="2026-09-01", race="Test Race", location="Minsk", location_be="Мінск",
                country="Belarus", country_be="Беларусь", dist="10", total_time="45:00",
                hr_avg="150", hr_max="170", elevation="0", sneakers="", video="", medal="", photos="")
    base.update(kw)
    for k, v in base.items():
        getattr(t, "v_" + k).set(v)


def fill_pb(t, history="", **kw):
    base = dict(distance="1 mile", distance_km="1.609", total_time="6:30", date="2026-09-01",
                race="Mile", location="Minsk", location_be="Мінск", country="Belarus",
                country_be="Беларусь", hr_avg="", hr_max="", sneakers="", video="", medal="", photos="")
    base.update(kw)
    for k, v in base.items():
        getattr(t, "v_" + k).set(v)
    t.prev_text.delete("1.0", "end")
    t.prev_text.insert("1.0", history)


def runs_on(d):
    return sorted(p.name for p in (SANDBOX / "data/runs").glob(f"{d}*.json"))


def feed_ids():
    a.write_data_js()
    xml = mf.build(mf.load_runs())
    return {t.split(" — ")[0]: i for t, i in
            re.findall(r"<title>(.*?)</title>\s*<id>tag:[^<]*:run/([^<]+)</id>", xml)}


def quiet(fn, *args):
    """Run a make_* main() without its progress output (the fixture's fake images fail
    to encode, which is expected and just noise here)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def rejects(fn, *args):
    try:
        fn(*args)
        return False
    except a.ValidationError:
        return True


APPS = []    # every App the tests create stays referenced until the end (see below)


def new_app():
    x = a.App()
    APPS.append(x)
    x.withdraw()
    deadline = time.time() + 5
    while x.refresher.busy and time.time() < deadline:
        time.sleep(0.02)
    return x


def test(name, gui=True):
    def deco(fn):
        if gui and app is None:
            SKIPPED.append(name)
            return fn
        try:
            fn()
        except Exception:
            RESULTS.append((name, False, traceback.format_exc()))
        return fn
    return deco


def write_record(rel, rec):
    (SANDBOX / rel).write_text(json.dumps(rec, ensure_ascii=False, indent=2), "utf-8")


def wait_idle(refresher):
    deadline = time.time() + 5
    while refresher.busy and time.time() < deadline:
        time.sleep(0.02)


# ══ No GUI needed ═════════════════════════════════════════════════════════════════

@test("validators", gui=False)
def _():
    for bad in ("abc", "1 000", "1_50", "-5", "0", "0.0", "nan", "inf", "1e3", "", "١٢", "+5", "5.", ".5"):
        check(f"distance {bad!r} rejected", rejects(a.parse_distance, bad))
    for good, v in (("10", 10.0), (" 21,1 ", 21.1), ("0.2", 0.2), ("42.195", 42.195)):
        check(f"distance {good!r} accepted", a.parse_distance(good) == v)
    for bad in ("abc", "1 000", "1_50", "-5", "nan", "1.5", "١٢٣", "+5"):
        check(f"HR {bad!r} rejected", rejects(a.parse_count, bad, "Avg HR"))
    for good, v in ((" 150 ", 150), ("", 0), ("0", 0)):
        check(f"HR {good!r} accepted", a.parse_count(good, "Avg HR") == v)
    for bad in ("abc", "1 000", "-5", "nan", "inf", "1e3", "12.", "+3"):
        check(f"elevation {bad!r} rejected", rejects(a.parse_elevation, bad))
    for good, v in (("320", 320), ("12.5", 12.5), ("12,5", 12.5), ("120.0", 120), ("", 0), (" 0 ", 0)):
        got = a.parse_elevation(good)
        check(f"elevation {good!r} accepted as {v!r}", got == v and type(got) is type(v), got)
    for bad in ("1:99:00", "19:60", "1:5:30", "0:00", "0:00:00", "abc", "", "19", "1:05:30:00", "-1:00",
                "19:14.", "19:14.1234", "１９:１４"):
        check(f"time {bad!r} rejected", rejects(a.parse_time, bad))
    for good in ("19:14", "1:05:30", "0:00:27.4", "0:11:43.18", "0:00:27.40", "10:00:00", "105:00"):
        check(f"time {good!r} accepted", a.parse_time(good) == good)
    for bad in ("../outside", "..\\outside", "2026-02-30", "2026-1-5", "20260105", "２０２６-０１-０５", "C:\\x", ""):
        check(f"date {bad!r} rejected", rejects(a.parse_date, bad))
    check("date is stripped", a.parse_date(" 2026-05-31 ") == "2026-05-31")
    for bad in ("..\\outside", "..", ".", "a:b", "x.", "con", "NUL.txt", "a*b", 'a"b', "", "   ", "tab\there"):
        check(f"PB label {bad!r} rejected", rejects(a.pb_slug, bad))
    for good, slug in (("5 km", "5_km"), ("21.1 км", "21.1_км"), ("1/2 Marathon", "12_marathon"),
                       ("../outside", "..outside")):
        check(f"PB label {good!r} -> {slug}", a.pb_slug(good) == slug)
    for same in ("5 km", "5km", "5 KM", "5  км", "5_км", "5,0 km", "5.0 км"):
        check(f"PB label {same!r} is the distance '5 km'", a.pb_key(same) == "5 km", a.pb_key(same))
    for label, key in (("21.1 km", "21.1 km"), ("21,1 км", "21.1 km"), ("200 м", "200 m"), ("0.20 km", "0.2 km"),
                       ("21.0975 km", "21.0975 km"), ("42.19512 km", "42.19512 km"), ("50 km", "50 km"),
                       ("Half  Marathon", "half marathon"), ("5000 m", "5000 m"), ("1.2.3 km", "1.2.3 km")):
        check(f"PB label {label!r} -> key {key!r}", a.pb_key(label) == key, a.pb_key(label))
    check("number_text shows whole floats as integers",
          [a.number_text(v) for v in (150.0, 150, 12.5, "", 0)] == ["150", "150", "12.5", "", "0"])
    e = ""
    try:
        a.parse_previous_records("19:36|2024-04-27|X\n20:21;2023-05-16;Y\n||\n19:99|2024-13-01|Z")
    except a.ValidationError as err:
        e = str(err)
    check("bad history lines are all reported by number", all(f"line {n}" in e for n in (2, 3, 4)), e)
    r = a.parse_previous_records("19:36|2024-04-27|Park | North\n\n  \n20:00 | 2023-01-01 | A|B|C")
    check("'|' in a history location is kept", [x["location"] for x in r] == ["Park | North", "A|B|C"], r)


@test("record schema", gui=False)
def _():
    base = {"date": "2026-01-01", "distance_km": 5.0, "total_time": "25:00"}
    ok_runs = [base, {**base, "hr_avg": 150.0, "elevation": 12.5}, {**base, "location": "", "photos": []},
               {**base, "total_time": "0:00:27.4", "id": "2026-01-01-2"}]
    for rec in ok_runs:
        check(f"usable run {json.dumps(rec)[:60]}", a.record_problem(rec, "run") is None, a.record_problem(rec, "run"))
    bad_runs = [({}, 'missing "date"'), ([1], "not a JSON object"), ({**base, "photos": None}, '"photos"'),
                ({**base, "date": 20260101}, '"date" must be text'), ({**base, "distance_km": True}, '"distance_km"'),
                ({**base, "distance_km": 0}, '"distance_km"'), ({**base, "total_time": "1:99:00"}, "total_time"),
                ({**base, "location": None}, '"location"'), ({**base, "hr_avg": "150"}, '"hr_avg"'),
                ({**base, "hr_avg": 150.5}, "whole number"), ({**base, "elevation": -1}, '"elevation"'),
                ({**base, "id": 5}, '"id"')]
    for rec, why in bad_runs:
        got = a.record_problem(rec, "run") or ""
        check(f"unusable run {json.dumps(rec)[:60]} -> {why}", why in got, got)
    pb = {**base, "distance": "5 km", "previous_records": [{"time": "19:36", "date": "2024-04-27", "location": "X"}]}
    check("usable PB", a.record_problem(pb, "pb") is None)
    check("PB without a label is unusable", 'missing "distance"' in (a.record_problem(base, "pb") or ""))
    check("PB with a bad history row is unusable", "previous_records #1" in
          (a.record_problem({**pb, "previous_records": [{"time": "x", "date": "2024-01-01"}]}, "pb") or ""))
    check("every fixture record is usable", not a.load_problems(), a.load_problems())
    huge = SANDBOX / "data/runs/huge.json"
    deep = SANDBOX / "data/runs/deep.json"
    huge.write_text('{"date": "2026-01-01", "distance_km": 5.0, "total_time": "25:00", "elevation": 1'
                    + "0" * 400 + "}", "utf-8")
    deep.write_text("[" * 100000 + "]" * 100000, "utf-8")
    try:
        problems = a.load_problems()
        check("a huge number and absurd nesting are reported, not crashed on",
              any("huge.json" in p for p in problems) and any("deep.json" in p for p in problems), problems)
    finally:
        huge.unlink()
        deep.unlink()


@test("file names and paths", gui=False)
def _():
    check("child_path refuses ..", rejects(a.child_path, a.RUNS_DIR, "../x.json"))
    try:
        a.delete_record(SANDBOX / "make_feed.py", a.RUNS_DIR)
        refused = False
    except OSError:
        refused = True
    check("delete_record only deletes records", refused and (SANDBOX / "make_feed.py").exists())
    path, others = a.run_target("2025-09-13")
    check("run_target: a second run that day gets _2 and sees the first",
          path.name == "2025-09-13_2.json" and [r["_path"].name for r in others] == ["2025-09-13.json"])
    old = next(r for r in a.load_all_runs() if r["_path"].stem == "2025-09-13")
    check("run_target: a run keeping its date keeps its file", a.run_target("2025-09-13", old) == (old["_path"], []))
    write_record("data/pbs/old_name.json", _pb("8 km", 8.0, "33:00", "2020-01-01"))
    write_record("data/pbs/8_km.json", _pb("8 km trail", 8.0, "40:00", "2020-01-01"))
    try:
        check("pbs_with_label finds a PB by its label, whatever the file",
              [p["_path"].name for p in a.pbs_with_label("8 KM")] == ["old_name.json"])
        check("free_pb_path skips a name taken by another PB", a.free_pb_path("8 km").name == "8_km_2.json")
        check("free_pb_path keeps a record's own file",
              a.free_pb_path("8 km", SANDBOX / "data/pbs/8_km.json").name == "8_km.json")
    finally:
        (SANDBOX / "data/pbs/old_name.json").unlink()
        (SANDBOX / "data/pbs/8_km.json").unlink()


@test("copying photos", gui=False)
def _():
    src = src_dir("direct")
    fake_image(src / "P1.jpg", b"p1")
    fake_image(src / "P1.png", b"p1png")
    fake_image(src / "p2.JPG", b"p2")
    (src / "notes.txt").write_text("x")
    old = time.time() - 400 * 86400
    os.utime(src / "p2.JPG", (old, old))
    first = a.copy_photos(src, "direct")
    again = a.copy_photos(src, "direct")
    folder = SANDBOX / "data/photos/direct"
    check("images copied, same stem with another extension renamed, non-images ignored",
          first == ["data/photos/direct/P1.jpg", "data/photos/direct/P1_2.png", "data/photos/direct/p2.JPG"], first)
    check("copying the same folder again reuses the files", again == first and len(os.listdir(folder)) == 3)
    check("copies get the current mtime", abs((folder / "p2.JPG").stat().st_mtime - time.time()) < 120)
    fake_image(src / "P1.jpg", b"changed")
    check("a different file under a taken name gets the next free name",
          a.copy_photos(src, "direct")[0] == "data/photos/direct/P1_3.jpg"
          and (folder / "P1.jpg").read_bytes().endswith(b"p1"))
    check("copying a folder onto itself adds nothing", len(a.copy_photos(folder, "direct")) == len(os.listdir(folder)))
    medal = a.copy_medal(fake_image(src_dir("medal_direct") / "m.PNG", b"medal"), "direct")
    check("a medal is copied as medal.<ext>", medal == "data/photos/direct/medal.png", medal)
    shutil.rmtree(folder)


@test("feed and preview files", gui=False)
def _():
    a.write_data_js()
    ids = [k for _, k in mf.assign_ids(mf.load_runs())]
    check("feed ids are unique and the fixture's are plain dates",
          len(set(ids)) == len(ids) == len(RUNS) and set(ids) == set(RUNS), ids)
    pair = [dict(_run("2026-05-05"), race_name="x"), dict(_run("2026-05-05"), race_name="y")]
    check("an unmarked same-day pair is published as date, date-2 in file order",
          [k for _, k in mf.assign_ids(pair)] == ["2026-05-05", "2026-05-05-2"])
    scratch = TMP / "feed"
    scratch.mkdir()
    saved = mf.DATA_JS, mf.OUT, mp.DATA_JS, mp.DIMS_JS, mp.PREVIEW_ROOT, mp.BASE_DIR
    mp.BASE_DIR = scratch
    mf.DATA_JS = mp.DATA_JS = scratch / "data.js"
    mf.OUT, mp.DIMS_JS, mp.PREVIEW_ROOT = scratch / "atom.xml", scratch / "photo-dims.js", scratch / "previews"
    try:
        tricky = [dict(_run("2026-01-01"), race_name='A "quoted" ]; race\\ with ] brackets', location="Мінск")]
        mf.DATA_JS.write_text("const RUNS_DATA = " + json.dumps(tricky, ensure_ascii=False, indent=2)
                              + ";\n\nconst PBS_DATA = [];\n", "utf-8")
        check("load_runs copes with ']' and '];' inside strings", mf.load_runs() == tricky)
        quiet(mf.main, [])
        one = mf.OUT.read_text("utf-8")
        mf.DATA_JS.write_text("const RUNS_DATA = [];\n\nconst PBS_DATA = [];\n", "utf-8")
        rc = quiet(mf.main, [])
        empty = mf.OUT.read_text("utf-8")
        check("a log with no runs writes a feed with no entries",
              one.count("<entry>") == 1 and rc == 0 and empty.count("<entry>") == 0 and "</feed>" in empty, rc)
        quiet(mf.main, [])
        check("regenerating the empty feed gives the same file", mf.OUT.read_text("utf-8") == empty)
        mp.DIMS_JS.write_text('const PHOTO_DIMS = {\n  "data/photos/x/a.jpg": [1,2]\n};\n', "utf-8")
        dims_before = mp.DIMS_JS.read_bytes()
        orphan = mp.PREVIEW_ROOT / "thumb/x/a.webp"
        orphan.parent.mkdir(parents=True)
        orphan.write_bytes(b"old preview")
        check("--dry-run with no referenced photos writes nothing",
              quiet(mp.main, ["--dry-run"]) == 0 and mp.DIMS_JS.read_bytes() == dims_before and orphan.exists())
        check("--prune with no referenced photos still removes orphaned previews",
              quiet(mp.main, ["--prune"]) == 0 and not orphan.exists())
        check("no referenced photos empties photo-dims.js", "data/photos" not in mp.DIMS_JS.read_text("utf-8"))
        mf.DATA_JS.unlink()
        check("a missing data.js is an error and keeps the feed",
              quiet(mf.main, []) == 1 and mf.OUT.read_text("utf-8") == empty)
        check("the editor reports that as a problem", quiet(a.refresh_feed) is not None)
        mf.DATA_JS.write_text("garbage", "utf-8")
        check("an unreadable data.js is an error too", quiet(mf.main, []) == 1)
    finally:
        mf.DATA_JS, mf.OUT, mp.DATA_JS, mp.DIMS_JS, mp.PREVIEW_ROOT, mp.BASE_DIR = saved
    js = SANDBOX / "data/data.js"
    good = js.read_bytes()
    js.write_bytes(good.decode("utf-8").encode("utf-16"))
    check("write_data_js rewrites a data.js that isn't UTF-8", a.write_data_js() is True and js.read_bytes() == good)
    check("write_data_js leaves an up-to-date data.js alone", a.write_data_js() is False)


@test("background pass (logic)", gui=False)
def _():
    calls = []
    def slow():
        calls.append(1)
        time.sleep(0.3)
    r = a.BackgroundRefresh(work=slow)
    r.request()
    time.sleep(0.05)
    r.request()
    r.request()
    wait_idle(r)
    check("requests during a pass fold into one more pass", not r.busy and len(calls) == 2, len(calls))
    r = a.BackgroundRefresh(work=lambda: 1 / 0)
    with contextlib.redirect_stdout(io.StringIO()):        # its console warning is expected
        r.request()
        wait_idle(r)
    check("a crashing pass is reported, not lost", not r.busy and "failed" in " ".join(r.problems), r.problems)
    real_feed, real_main = a.refresh_feed, mp.main
    try:
        mp.main = lambda argv=None: 1                 # refresh_previews imports this module
        msg = quiet(a.refresh_previews)
        check("a preview run that fails is reported", bool(msg) and "previews" in msg, msg)
        def crash(argv=None):
            raise RuntimeError("magick exploded")
        mp.main = crash
        check("a preview run that crashes is reported with the reason",
              "magick exploded" in (quiet(a.refresh_previews) or ""))
        a.refresh_feed = lambda: "atom.xml not regenerated — stub"
        both = quiet(a.refresh_generated)
        check("refresh_generated returns every problem",
              len(both) == 2 and "magick exploded" in both[0] and both[1] == "atom.xml not regenerated — stub", both)
    finally:
        a.refresh_feed, mp.main = real_feed, real_main


# ══ Saving never loses a record ═════════════════════════════════════════════════

@test("unchanged saves")
def _():
    for d, select in (("runs", select_run), ("pbs", select_pb)):
        for p in sorted((SANDBOX / "data" / d).glob("*.json")):
            before = p.read_bytes()
            t = select(p.stem)
            LOG.clear()
            t._save()
            check(f"open + save unchanged keeps {d}/{p.name} byte-identical",
                  p.read_bytes() == before and last()[0] == "info", LOG[-1:])
    check("no stray files in runs/", all(f.suffix == ".json" for f in (SANDBOX / "data/runs").iterdir()))


@test("medal")
def _():
    os.chdir(tempfile.gettempdir())
    try:
        t = select_run("2024-06-08")
        t.v_race.set("Edited from another cwd")
        LOG.clear()
        t._save()
        r = rjson("data/runs/2024-06-08.json")
        check("edit with an unchanged medal from another cwd saves and keeps the medal",
              last()[0] == "info" and r["medal"] == "data/photos/2024-06-08/medal.jpg"
              and r["race_name"] == "Edited from another cwd", LOG)
    finally:
        os.chdir(SANDBOX)
    medal = RUNS["2024-05-26"]["medal"]
    pics = photos_snapshot()
    for variant in (str((SANDBOX / medal).resolve()), medal.replace("/", "\\"), str(SANDBOX / medal).upper()):
        t = select_run("2024-05-26")
        t.v_medal.set(variant)
        LOG.clear()
        t._save()
        check(f"re-picking the same medal ({variant[-25:]}) keeps it",
              last()[0] == "info" and rjson("data/runs/2024-05-26.json")["medal"] == medal, LOG)
    check("re-picking the same medal copies nothing", photos_snapshot() == pics)

    old_bytes = (SANDBOX / medal).read_bytes()
    src = fake_image(src_dir("medal") / "new.JPG", b"a different medal")
    t = select_run("2024-05-26")
    t.v_medal.set(str(src))
    t._save()
    r = rjson("data/runs/2024-05-26.json")
    check("a different medal gets a free name", r["medal"] == "data/photos/2024-05-26/medal_2.jpg", r["medal"])
    check("the old medal file is untouched", (SANDBOX / medal).read_bytes() == old_bytes)

    snap = snapshot()
    t = select_run("2024-06-16")
    t.v_medal.set("C:/nope/medal.jpg")
    LOG.clear()
    t._save()
    check("a missing medal file blocks the save", last()[0] == "error" and "Medal photo" in last()[2]
          and snapshot() == snap, LOG)


@test("failures keep the old record")
def _():
    photos = src_dir("copyfail")
    fake_image(photos / "a.jpg", b"aaa")
    snap = snapshot()
    real_copy = a.shutil.copy2
    a.shutil.copy2 = lambda *x, **k: (_ for _ in ()).throw(PermissionError(32, "in use"))
    try:
        t = select_run("2024-06-08")
        t.v_race.set("must not persist")
        t.v_photos.set(str(photos))
        LOG.clear()
        t._save()
    finally:
        a.shutil.copy2 = real_copy
    check("copy failure: error, records unchanged", last()[0] == "error"
          and "No existing record was changed" in last()[2] and snapshot() == snap, LOG)

    real_replace = a.os.replace
    a.os.replace = lambda *x, **k: (_ for _ in ()).throw(OSError(28, "No space left on device"))
    try:
        t = select_run("2024-06-08")
        t.v_date.set("2024-06-09")
        LOG.clear()
        t._save()
        t = select_pb("10_km")
        t.v_distance.set("10 km road")
        t._save()
    finally:
        a.os.replace = real_replace
    check("write failure (run move, PB rename): errors, records unchanged",
          [e[0] for e in LOG] == ["error", "error"] and snapshot() == snap, LOG)
    check("write failure leaves no temp files",
          not [f for d in ("runs", "pbs") for f in (SANDBOX / "data" / d).iterdir() if f.suffix != ".json"])

    real_unlink = Path.unlink
    def unlink(self, *x, **k):
        if self.suffix == ".json":
            raise PermissionError(5, "Access is denied")
        return real_unlink(self, *x, **k)
    Path.unlink = unlink
    try:
        t = select_run("2024-06-16")
        t.v_date.set("2024-06-17")
        LOG.clear()
        t._save()
    finally:
        Path.unlink = real_unlink
    check("old file can't be removed after a move: warned, both files kept",
          last()[0] == "info" and "could not be removed" in last()[2]
          and (SANDBOX / "data/runs/2024-06-17.json").exists()
          and (SANDBOX / "data/runs/2024-06-16.json").exists(), LOG)
    (SANDBOX / "data/runs/2024-06-17.json").unlink()


# ══ Clashes ═══════════════════════════════════════════════════════════════════════

@test("same-day runs")
def _():
    first = (SANDBOX / "data/runs/2025-09-13.json").read_bytes()
    t = app.run_tab
    fill_run(t, date="2025-09-13", race="Second")
    ANSWER["yes"] = False
    LOG.clear()
    t._save()
    check("second run that day: asks; No writes nothing",
          LOG[0][0] == "ask" and runs_on("2025-09-13") == ["2025-09-13.json"], LOG)
    ANSWER["yes"] = True
    photos = src_dir("second")
    fake_image(photos / "IMG_1.jpg", b"second-run photo")
    fill_run(t, date="2025-09-13", race="Second", photos=str(photos))
    t._save()
    second = rjson("data/runs/2025-09-13_2.json")
    check("Yes saves it as _2 with its own photo folder and feed id",
          runs_on("2025-09-13") == ["2025-09-13.json", "2025-09-13_2.json"]
          and second["photos"] == ["data/photos/2025-09-13_2/IMG_1.jpg"] and second.get("id") == "2025-09-13-2",
          (runs_on("2025-09-13"), second))
    check("the first run is untouched", (SANDBOX / "data/runs/2025-09-13.json").read_bytes() == first)

    target = (SANDBOX / "data/runs/2025-01-25.json").read_bytes()
    t = select_run("2024-12-21")
    t.v_date.set("2025-01-25")
    ANSWER["yes"] = False
    LOG.clear()
    t._save()
    check("moving onto an occupied date asks; No changes nothing",
          LOG[0][0] == "ask" and (SANDBOX / "data/runs/2024-12-21.json").exists(), LOG)
    ANSWER["yes"] = True
    t = select_run("2024-12-21")
    t.v_date.set("2025-01-25")
    t._save()
    check("Yes moves it to _2 and leaves the other run alone",
          (SANDBOX / "data/runs/2025-01-25_2.json").exists() and not (SANDBOX / "data/runs/2024-12-21.json").exists()
          and (SANDBOX / "data/runs/2025-01-25.json").read_bytes() == target)
    t = select_run("2025-01-25_2")
    t.v_date.set("2024-12-21")
    LOG.clear()
    t._save()
    check("moving back to a free date takes the plain name, without asking",
          (SANDBOX / "data/runs/2024-12-21.json").exists() and not any(e[0] == "ask" for e in LOG))


@test("adding a PB for an existing distance")
def _():
    p = SANDBOX / "data/pbs/5_км.json"
    orig, cur = p.read_bytes(), json.loads(p.read_bytes())
    t = app.pb_tab
    for label in ("5 км", "5_км", "5 КМ"):
        fill_pb(t, distance=label, distance_km="5", total_time="18:59", date="2026-09-10")
        ANSWER["yes"] = False
        LOG.clear()
        t._save()
        check(f"'{label}' is the same distance as '5 км': asks; No changes nothing",
              LOG[0][0] == "ask" and p.read_bytes() == orig, LOG)
    fill_pb(t, distance="5 км", distance_km="5", total_time="18:59", date="2026-09-10",
            history="17:00|2021-01-01|Old town")
    ANSWER["yes"] = True
    t._save()
    new = json.loads(p.read_text("utf-8"))
    hist = new["previous_records"]
    check("Yes replaces the PB and keeps the old result, old history and typed lines, newest first",
          new["total_time"] == "18:59"
          and {"time": cur["total_time"], "date": cur["date"], "location": cur["location"]} in hist
          and all(r in hist for r in cur["previous_records"])
          and {"time": "17:00", "date": "2021-01-01", "location": "Old town"} in hist
          and [r["date"] for r in hist] == sorted((r["date"] for r in hist), reverse=True), hist)
    fill_pb(t, distance="5 км", distance_km="5", total_time="25:00", date="2026-09-11")
    ANSWER["yes"] = False
    LOG.clear()
    t._save()
    check("a slower time is pointed out", "not faster" in LOG[0][2], LOG)
    ANSWER["yes"] = True


@test("PB identified by its label, not its file name")
def _():
    legacy = SANDBOX / "data/pbs/legacy_mile.json"
    legacy.write_text(json.dumps(_pb("1 mile", 1.609, "6:40", "2020-05-01"), ensure_ascii=False, indent=2), "utf-8")
    before = snapshot()
    t = app.pb_tab
    fill_pb(t, distance="1 Mile", total_time="6:20", date="2026-09-12")
    ANSWER["yes"] = False
    LOG.clear()
    t._save()
    check("a PB in a file with an old-style name is found: asks; No changes nothing",
          LOG and LOG[0][0] == "ask" and snapshot() == before, LOG)
    ANSWER["yes"] = True
    t._save()
    rec = json.loads(legacy.read_text("utf-8"))
    check("Yes updates that file, with the old result in the history — one PB for the distance",
          rec["total_time"] == "6:20" and {"time": "6:40", "date": "2020-05-01", "location": "Batumi"} in rec["previous_records"]
          and not (SANDBOX / "data/pbs/1_mile.json").exists()
          and sum(1 for p in a.load_all_pbs() if a.pb_key(p["distance"]) == "1 mile") == 1, rec)

    twin = SANDBOX / "data/pbs/mile_copy.json"
    twin.write_text(json.dumps(_pb("1 mile", 1.609, "7:00", "2019-01-01"), ensure_ascii=False, indent=2), "utf-8")
    before = snapshot()
    fill_pb(t, distance="1 mile", total_time="6:10", date="2026-09-13")
    LOG.clear()
    t._save()
    check("two PBs already for the distance: refused, naming both files",
          last()[0] == "error" and "legacy_mile.json" in last()[2] and "mile_copy.json" in last()[2]
          and snapshot() == before, LOG)
    twin.unlink()

    squatter = SANDBOX / "data/pbs/7_km.json"
    squatter.write_text(json.dumps(_pb("7 km trail", 7.0, "35:00", "2022-01-01"), ensure_ascii=False, indent=2), "utf-8")
    sq = squatter.read_bytes()
    fill_pb(t, distance="7 km", distance_km="7", total_time="30:00", date="2026-09-14")
    LOG.clear()
    t._save()
    check("a new distance whose file name is taken by another PB gets a free name",
          last()[0] == "info" and squatter.read_bytes() == sq
          and json.loads((SANDBOX / "data/pbs/7_km_2.json").read_text("utf-8"))["distance"] == "7 km", LOG)

    before = snapshot()
    t = select_pb("3_km")
    t.v_distance.set("1 MILE")
    LOG.clear()
    t._save()
    check("renaming a PB onto a distance that has one (in any file) is refused",
          last()[0] == "error" and "legacy_mile.json" in last()[2] and snapshot() == before, LOG)
    t = select_pb("3_km")
    t.v_distance.set("3 km track")
    t._save()
    check("renaming to a free distance moves the file",
          (SANDBOX / "data/pbs/3_km_track.json").exists() and not (SANDBOX / "data/pbs/3_km.json").exists())
    t = select_pb("3_km_track")
    t.v_distance.set("3 km")
    t._save()
    t = select_pb("legacy_mile")
    t.v_race.set("edited")
    t._save()
    check("editing a PB in an old-style file keeps that file",
          json.loads(legacy.read_text("utf-8"))["race_name"] == "edited" and not (SANDBOX / "data/pbs/1_mile.json").exists())


@test("PB labels spelt differently are one distance")
def _():
    x = quiet(new_app)
    check("the Add PB form starts with an empty label", x.pb_tab.v_distance.get() == "")
    x.destroy()
    t = app.pb_tab
    before = snapshot()
    ANSWER["yes"] = False
    for label, km in (("5 km", "5"), ("5km", "5"), ("5  км", "5"), ("5,0 km", "5"), ("21.1 km", "21.1")):
        fill_pb(t, distance=label, distance_km=km, total_time="0:18:00", date="2026-09-16")
        LOG.clear()
        t._save()
        check(f"'{label}' is found as the existing PB: asks; No changes nothing",
              LOG and LOG[0][0] == "ask" and snapshot() == before, LOG)
    ANSWER["yes"] = True
    t = select_pb("3_km")
    t.v_distance.set("5 km")
    LOG.clear()
    t._save()
    check("renaming 3 km to '5 km' is refused while '5 км' exists", last()[0] == "error" and snapshot() == before, LOG)
    t = select_pb("5_км")
    t.v_distance.set("5 km")
    LOG.clear()
    t._save()
    check("respelling '5 км' as '5 km' keeps its file", last()[0] == "info"
          and rjson("data/pbs/5_км.json")["distance"] == "5 km" and not (SANDBOX / "data/pbs/5_km.json").exists(), LOG)
    t = select_pb("5_км")
    t.v_distance.set("5 км")
    t._save()


@test("a PB file that can't be loaded blocks adding that distance")
def _():
    p = SANDBOX / "data/pbs/5_км.json"
    orig = p.read_bytes()
    rec = json.loads(orig)
    rec["photos"] = None
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2), "utf-8")
    try:
        before = snapshot()
        fill_pb(app.pb_tab, distance="5 км", distance_km="5", total_time="0:18:00", date="2026-09-15")
        LOG.clear()
        app.pb_tab._save()
        check("Add PB refuses and names the file", last()[0] == "error" and "5_км.json" in last()[2]
              and snapshot() == before, LOG)
        t = select_pb("3_km")
        t.v_distance.set("5 km")
        LOG.clear()
        t._save()
        check("renaming a PB is refused too", last()[0] == "error" and "5_км.json" in last()[2]
              and snapshot() == before, LOG)
    finally:
        p.write_bytes(orig)


@test("a broken sneakers.json")
def _():
    f = SANDBOX / "data/sneakers.json"
    orig = f.read_bytes()
    try:
        for i, bad in enumerate(('["Shoe A", "Shoe B",]', "{}")):
            f.write_text(bad, "utf-8")
            x = quiet(new_app)
            check(f"the editor opens with sneakers.json = {bad!r}, dropdown empty", not x.run_tab.cb_sneakers["values"])
            x.destroy()
            fill_run(app.run_tab, date=f"2026-08-2{i + 1}", race="Shoes", sneakers="Brand New Shoe")
            LOG.clear()
            quiet(app.run_tab._save)
            check(f"a save with sneakers.json = {bad!r} completes and leaves the file alone",
                  last()[0] == "info" and (SANDBOX / f"data/runs/2026-08-2{i + 1}.json").exists()
                  and f.read_text("utf-8") == bad, LOG)
    finally:
        f.write_bytes(orig)


@test("records with optional fields missing, or numbers stored as floats")
def _():
    minimal = {"date": "2026-02-02", "distance_km": 5.0, "total_time": "25:00"}
    write_record("data/runs/2026-02-02.json", minimal)
    write_record("data/runs/2026-02-03.json", dict(minimal, date="2026-02-03"))
    t = select_run("2026-02-02")
    LOG.clear()
    t._save()
    check("a run with only date, distance and time opens and saves",
          last()[0] == "info" and rjson("data/runs/2026-02-02.json")["total_time"] == "25:00", LOG)
    t = select_run("2026-02-03")
    ANSWER["yes"] = False
    LOG.clear()
    t._delete()
    check("deleting a run without a location asks; No keeps it",
          [e[0] for e in LOG] == ["ask"] and (SANDBOX / "data/runs/2026-02-03.json").exists(), LOG)
    ANSWER["yes"] = True
    t = select_run("2026-02-03")
    LOG.clear()
    t._delete()
    check("Yes deletes exactly that file", not (SANDBOX / "data/runs/2026-02-03.json").exists()
          and (SANDBOX / "data/runs/2026-02-02.json").exists() and "2026-02-03.json" in last()[2], LOG)

    write_record("data/runs/2026-02-04.json", _run("2026-02-04", hr_avg=150.0, hr_max=170, elevation=12.5))
    t = select_run("2026-02-04")
    check("the form shows 150.0 as 150 and keeps 12.5", (t.v_hr_avg.get(), t.v_elevation.get()) == ("150", "12.5"))
    t.v_race.set("renamed only")
    LOG.clear()
    t._save()
    rec = rjson("data/runs/2026-02-04.json")
    check("changing another field saves without a complaint about HR or elevation",
          last()[0] == "info" and rec["hr_avg"] == 150 and type(rec["hr_avg"]) is int and rec["elevation"] == 12.5,
          (LOG, rec))
    write_record("data/pbs/9_km.json", dict(_pb("9 km", 9.0, "38:00", "2021-01-01"), hr_max=180.0))
    t = select_pb("9_km")
    LOG.clear()
    t._save()
    check("a PB with a float heart rate saves too",
          last()[0] == "info" and rjson("data/pbs/9_km.json")["hr_max"] == 180, LOG)
    write_record("data/runs/2026-02-05.json", _run("2026-02-05", hr_avg=150.5))
    try:
        problems = a.load_problems()
        check("a fractional heart rate is refused when loading, with the reason",
              any("2026-02-05.json" in p and "whole number" in p for p in problems), problems)
    finally:
        for rel in ("data/runs/2026-02-02.json", "data/runs/2026-02-04.json", "data/runs/2026-02-05.json",
                    "data/pbs/9_km.json"):
            (SANDBOX / rel).unlink(missing_ok=True)
        a.write_data_js()


# ══ Input ═════════════════════════════════════════════════════════════════════════

@test("ids that could leave the data folder")
def _():
    for bad in ("../outside", "..\\outside", "2026-02-30", "2026-1-5", "20260105", "２０２６-０１-０５", "C:\\x", ""):
        check(f"date {bad!r} rejected", rejects(a.parse_date, bad))
    check("date is stripped", a.parse_date(" 2026-05-31 ") == "2026-05-31")
    check("'../outside' as a PB label stays a single name inside data/pbs",
          a.pb_slug("../outside") == "..outside" and a.free_pb_path("../outside").parent == a.PBS_DIR)
    for bad in ("..\\outside", "..", ".", "a:b", "x.", "con", "NUL.txt", "a*b", 'a"b', "", "   ", "tab\there"):
        check(f"PB label {bad!r} rejected", rejects(a.pb_slug, bad))
    for good, slug in (("5 km", "5_km"), ("21.1 км", "21.1_км"), ("1/2 Marathon", "12_marathon")):
        check(f"PB label {good!r} -> {slug}", a.pb_slug(good) == slug)
    check("child_path refuses ..", rejects(a.child_path, a.RUNS_DIR, "../x.json"))
    snap = snapshot()
    fill_run(app.run_tab, date="../outside")
    LOG.clear()
    app.run_tab._save()
    fill_pb(app.pb_tab, distance="..\\outside")
    app.pb_tab._save()
    check("the GUI refuses them and writes nothing", [e[0] for e in LOG] == ["error", "error"] and snapshot() == snap, LOG)


@test("field validation")
def _():
    for bad in ("abc", "1 000", "1_50", "-5", "0", "0.0", "nan", "inf", "1e3", "", "١٢", "+5", "5.", ".5"):
        check(f"distance {bad!r} rejected", rejects(a.parse_distance, bad))
    for good, v in (("10", 10.0), (" 21,1 ", 21.1), ("0.2", 0.2), ("42.195", 42.195)):
        check(f"distance {good!r} accepted", a.parse_distance(good) == v)
    for bad in ("abc", "1 000", "1_50", "-5", "nan", "1.5", "١٢٣", "+5"):
        check(f"HR {bad!r} rejected", rejects(a.parse_count, bad, "Avg HR"))
    for good, v in ((" 150 ", 150), ("", 0), ("0", 0)):
        check(f"HR {good!r} accepted", a.parse_count(good, "Avg HR") == v)
    for bad in ("1:99:00", "19:60", "1:5:30", "0:00", "0:00:00", "abc", "", "19", "1:05:30:00", "-1:00",
                "19:14.", "19:14.1234", "１９:１４"):
        check(f"time {bad!r} rejected", rejects(a.parse_time, bad))
    for good in ("19:14", "1:05:30", "0:00:27.4", "0:11:43.18", "0:00:27.40", "10:00:00", "105:00"):
        check(f"time {good!r} accepted", a.parse_time(good) == good)
    snap = snapshot()
    fill_run(app.run_tab, dist="nan", total_time="1:99:00", hr_avg="abc", hr_max="-5", elevation="1 000", date="2026-02-30")
    LOG.clear()
    app.run_tab._save()
    msg = last()[2]
    check("every bad field is listed in one dialog, nothing written",
          last()[0] == "error" and snapshot() == snap
          and all(s in msg for s in ("Date", "Distance", "Total time", "Avg HR", "Max HR", "Elevation")), msg)
    try:
        a.write_json(TMP / "nan.json", {"x": float("nan")})
        refused = False
    except ValueError:
        refused = True
    check("write_json refuses NaN", refused and not (TMP / "nan.json").exists())


@test("PB history lines")
def _():
    def error_of(text):
        try:
            a.parse_previous_records(text)
            return ""
        except a.ValidationError as e:
            return str(e)
    check("a ';' line is reported with its number", "line 2" in error_of("19:36|2024-04-27|X\n20:21;2023-05-16;Y\n"))
    check("'||' is rejected", "line 1" in error_of("||\n"))
    e = error_of("19:36|2024-13-01|X\n19:99|2024-01-01|Y")
    check("bad date and bad time are both reported", "line 1" in e and "line 2" in e, e)
    r = a.parse_previous_records("19:36|2024-04-27|Park | North\n\n  \n20:00 | 2023-01-01 | A|B|C")
    check("'|' in a location is kept", [x["location"] for x in r] == ["Park | North", "A|B|C"], r)
    before = (SANDBOX / "data/pbs/10_km.json").read_bytes()
    t = select_pb("10_km")
    t.prev_text.insert("end", "41:00;2022-01-01;Oops\n")
    LOG.clear()
    t._save()
    check("a bad line blocks Save Changes", last()[0] == "error" and (SANDBOX / "data/pbs/10_km.json").read_bytes() == before, LOG)
    t = select_pb("10_km")
    t.prev_text.delete("1.0", "end")
    t.prev_text.insert("1.0", "41:00|2022-01-01|A | B\n")
    t._save()
    select_pb("10_km")._save()
    check("a location with '|' survives open + save",
          rjson("data/pbs/10_km.json")["previous_records"] == [{"time": "41:00", "date": "2022-01-01", "location": "A | B"}])


# ══ Deleting ══════════════════════════════════════════════════════════════════════

@test("delete")
def _():
    legacy, canon = SANDBOX / "data/runs/2026-06-01_1200.json", SANDBOX / "data/runs/2026-06-01.json"
    legacy.write_text(json.dumps(_run("2026-06-01", location="Legacy")), "utf-8")
    canon.write_text(json.dumps(_run("2026-06-01", location="Canon")), "utf-8")
    canon_bytes = canon.read_bytes()
    t = select_run("2026-06-01_1200")
    t.v_race.set("Legacy edited")
    t._save()
    check("editing a run in an old-style file keeps that file", rjson("data/runs/2026-06-01_1200.json")["race_name"] == "Legacy edited"
          and canon.read_bytes() == canon_bytes)
    t = select_run("2026-06-01_1200")
    LOG.clear()
    t._delete()
    check("delete removes that file, not the other run of the day",
          not legacy.exists() and canon.read_bytes() == canon_bytes and "2026-06-01_1200.json" in last()[2], LOG)
    t = select_run("2026-06-01")
    canon.unlink()
    LOG.clear()
    t._delete()
    check("a file that is already gone is reported honestly", last()[0] == "info" and "already been removed" in last()[2], LOG)
    t = select_pb("200_m")
    real_unlink = Path.unlink
    Path.unlink = lambda self, *x, **k: (_ for _ in ()).throw(PermissionError(5, "Access is denied"))
    try:
        LOG.clear()
        t._delete()
    finally:
        Path.unlink = real_unlink
    check("a failed delete shows only an error", [e[0] for e in LOG] == ["ask", "error"], LOG)
    try:
        a.delete_record(SANDBOX / "make_feed.py", a.RUNS_DIR)
        refused = False
    except OSError:
        refused = True
    check("delete_record only deletes records", refused and (SANDBOX / "make_feed.py").exists())


# ══ Photos ════════════════════════════════════════════════════════════════════════

@test("photos")
def _():
    src = src_dir("photos")
    fake_image(src / "IMG_5.jpg", b"one")
    fake_image(src / "IMG_6.PNG", b"two")
    (src / "notes.txt").write_text("x")
    folder = SANDBOX / "data/photos/2025-11-22"
    for _ in range(2):
        t = select_run("2025-11-22")
        t.v_photos.set(str(src))
        t._save()
    r = rjson("data/runs/2025-11-22.json")
    check("photos are added once, however often the folder is picked",
          r["photos"] == ["data/photos/2025-11-22/IMG_9.jpg", "data/photos/2025-11-22/IMG_5.jpg", "data/photos/2025-11-22/IMG_6.PNG"]
          and sorted(os.listdir(folder)) == ["IMG_5.jpg", "IMG_6.PNG", "IMG_9.jpg"], (r["photos"], os.listdir(folder)))
    fake_image(src / "IMG_5.jpg", b"one, but different")
    t = select_run("2025-11-22")
    t.v_photos.set(str(src))
    t._save()
    r = rjson("data/runs/2025-11-22.json")
    check("a different file with a taken name gets the next free name",
          "data/photos/2025-11-22/IMG_5_2.jpg" in r["photos"] and (folder / "IMG_5.jpg").read_bytes().endswith(b"one"), r["photos"])
    n = len(r["photos"])
    t = select_run("2025-11-22")
    t.v_photos.set(str(folder))
    t._save()
    check("picking the event's own folder adds nothing", len(rjson("data/runs/2025-11-22.json")["photos"]) == n)
    fake_image(src_dir("case") / "img_5.JPG", b"one")
    t = select_run("2025-11-22")
    t.v_photos.set(str(src_dir("case")))
    t._save()
    check("an identical file differing only in case is reused with its on-disk spelling",
          len(rjson("data/runs/2025-11-22.json")["photos"]) == n)

    stems = src_dir("stems")
    for name, data in (("IMG_1.jpg", b"jpg"), ("IMG_1.png", b"png"), ("img_2.JPG", b"j2"), ("IMG_2.webp", b"w2")):
        fake_image(stems / name, data)
    fill_run(app.run_tab, date="2026-07-20", race="Stems", photos=str(stems))
    app.run_tab._save()
    check("IMG_1.png next to IMG_1.jpg gets its own stem (they'd share a preview)",
          rjson("data/runs/2026-07-20.json")["photos"] == [
              "data/photos/2026-07-20/IMG_1.jpg", "data/photos/2026-07-20/IMG_1_2.png",
              "data/photos/2026-07-20/img_2.JPG", "data/photos/2026-07-20/IMG_2_2.webp"])
    a.write_data_js()
    dests = [mp.dest_for(r, "thumb") for r in mp.referenced_paths()]
    check("no two referenced images share a preview", len(set(dests)) == len(dests))

    old = fake_image(src_dir("old") / "OLD_1.jpg", b"old camera file")
    os.utime(old, (time.time() - 400 * 86400,) * 2)
    fill_run(app.run_tab, date="2026-06-20", race="Mtime", photos=str(old.parent))
    app.run_tab._save()
    check("a copied photo gets the current mtime (so no stale preview is kept)",
          abs((SANDBOX / "data/photos/2026-06-20/OLD_1.jpg").stat().st_mtime - time.time()) < 120)
    t = select_run("2025-11-22")
    t.v_photos.set("C:/definitely/not/here")
    LOG.clear()
    t._save()
    check("a missing photos folder is an error", last()[0] == "error" and "Photos folder" in last()[2], LOG)


# ══ Feed ids ══════════════════════════════════════════════════════════════════════

@test("feed ids")
def _():
    D = "2026-07-01"
    fill_run(app.run_tab, date=D, race="RaceA")
    app.run_tab._save()
    fill_run(app.run_tab, date=D, race="RaceB")
    app.run_tab._save()
    ids = feed_ids()
    check("same day: first keeps the date, second gets -2", (ids["RaceA"], ids["RaceB"]) == (D, D + "-2"), ids)
    t = select_run(D)
    t.v_date.set("2026-07-02")
    t._save()
    check("a moved run stores the id it was published under", rjson("data/runs/2026-07-02.json").get("id") == D)
    fill_run(app.run_tab, date=D, race="RaceC")
    app.run_tab._save()
    t = select_run(D + "_2")
    t.v_date.set("2026-07-03")
    t._save()
    ids = feed_ids()
    check("ids never move between runs", (ids["RaceA"], ids["RaceB"], ids["RaceC"]) == (D, D + "-2", D + "-3")
          and len(set(ids.values())) == len(ids), ids)

    H = "2026-06-11"
    (SANDBOX / f"data/runs/{H}.json").write_text(json.dumps(_run(H, race_name="HandX")), "utf-8")
    (SANDBOX / f"data/runs/{H}_2.json").write_text(json.dumps(_run(H, race_name="HandY")), "utf-8")
    quiet(new_app).destroy()
    check("a hand-made _2 file gets its published id stored at startup",
          rjson(f"data/runs/{H}_2.json").get("id") == H + "-2" and "id" not in rjson(f"data/runs/{H}.json"))
    select_run(H)._delete()
    check("deleting the first run of that day doesn't move the second one's id", feed_ids()["HandY"] == H + "-2")


# ══ Broken files ══════════════════════════════════════════════════════════════════

def broken_files_checks(broken):
    data_js = (SANDBOX / "data/data.js").read_bytes()
    raw = {rel: (SANDBOX / rel).read_bytes() for rel in broken}
    LOG.clear()
    x = quiet(new_app)
    warn = last("warn")
    check("startup warns once, naming every broken file and why",
          warn is not None and all(Path(rel).name in warn[2] for rel in broken)
          and 'missing "date"' in warn[2] and '"photos" must be a list' in warn[2], LOG)
    check("the tabs open with the good records", len(x.edit_run_tab.runs) == len(a.load_all_runs()) > 5
          and len(x.edit_pb_tab.pbs) == len(a.load_all_pbs()))
    check("View All lists the skipped files", "broken_empty.json" in x.view_tab.text.get("1.0", "end"))
    x.destroy()
    check("data.js is not rebuilt without them", (SANDBOX / "data/data.js").read_bytes() == data_js)
    fill_run(app.run_tab, date="2026-08-01", race="WhileBroken")
    LOG.clear()
    app.run_tab._save()
    check("a save still writes the record, and the data.js dialog names the broken files",
          (SANDBOX / "data/runs/2026-08-01.json").exists() and [e[0] for e in LOG] == ["retry"]
          and "broken_empty.json" in LOG[0][2], LOG)
    check("the broken files are never rewritten", all((SANDBOX / rel).read_bytes() == b for rel, b in raw.items()))


@test("broken record files")
def _():
    broken = {
        "data/runs/broken_empty.json": "{}",
        "data/runs/broken_photos.json": json.dumps(_run("2026-03-03", photos=None)),
        "data/runs/broken_syntax.json": '{"date": "2026-03-04",',
        "data/pbs/broken_pb.json": json.dumps({"date": "2026-03-05", "distance_km": 5.0, "total_time": "20:00"}),
    }
    for rel, text in broken.items():
        (SANDBOX / rel).write_text(text, "utf-8")
    try:
        broken_files_checks(broken)
    finally:
        for rel in broken:
            (SANDBOX / rel).unlink(missing_ok=True)
    LOG.clear()
    new_app().destroy()
    check("once they are gone, the next start rebuilds data.js with the new run",
          not LOG and "WhileBroken" in (SANDBOX / "data/data.js").read_text("utf-8"), LOG)


# ══ data.js ═══════════════════════════════════════════════════════════════════════

@test("data.js")
def _():
    real = a.write_data_js
    calls = {"n": 0}
    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(13, "The file is locked")
        return real()
    a.write_data_js = flaky
    RETRY["yes"] = True
    try:
        fill_run(app.run_tab, date="2026-07-10", race="RetryRace")
        LOG.clear()
        app.run_tab._save()
    finally:
        a.write_data_js = real
        RETRY["yes"] = False
    msg = next((e[2] for e in LOG if e[0] == "retry"), "")
    check("a failed rebuild offers Retry and never says 'save again'",
          [e[0] for e in LOG] == ["retry", "info"] and "record itself is saved" in msg and "save again" not in msg.lower(), LOG)
    js = SANDBOX / "data/data.js"
    good = js.read_bytes()
    for enc in ("utf-16", "cp1251"):
        js.write_bytes(good.decode("utf-8").encode(enc, errors="replace"))
        new_app().destroy()
        check(f"a data.js re-saved as {enc} is rewritten as UTF-8 at startup", js.read_bytes() == good)
    m = js.stat().st_mtime_ns
    before = len(REFRESHES)
    new_app().destroy()
    check("a start with data.js in sync rewrites nothing but still runs one preview/feed pass",
          js.stat().st_mtime_ns == m and len(REFRESHES) == before + 1)


# ══ Background pass ═══════════════════════════════════════════════════════════════

@test("status line")
def _():
    x = new_app()

    def pump_until(cond):
        """Run the real Tk event loop (so after() polls fire) until cond() holds."""
        deadline = time.time() + 5
        while not cond() and time.time() < deadline:
            x.update()
            time.sleep(0.02)
        return cond()

    pump_until(lambda: not x._polling)
    outcome = {"problems": ["atom.xml not regenerated — test"]}
    x.refresher = a.BackgroundRefresh(work=lambda: (time.sleep(0.3), outcome["problems"])[1])
    x.start_refresh()
    check("while a pass runs the status says so, without Retry",
          x.status.get().startswith("Updating") and x.retry_button.winfo_manager() == "", x.status.get())
    check("when it fails, the warning and Retry appear by themselves",
          pump_until(lambda: "atom.xml not regenerated" in x.status.get()) and x.retry_button.winfo_manager() == "pack",
          x.status.get())
    outcome["problems"] = []
    x.retry_button.invoke()
    check("Retry runs the pass again and the warning goes by itself",
          pump_until(lambda: x.status.get() == "") and x.retry_button.winfo_manager() == "", x.status.get())
    outcome["problems"] = ["still failing"]
    x.deiconify()
    x.geometry(f"{max(x.winfo_reqwidth(), 520)}x420")        # far below its natural height
    x.start_refresh()
    pump_until(lambda: "still failing" in x.status.get())
    x.update()
    check("on a short window the status line and Retry stay visible",
          x.status_label.winfo_ismapped() and x.retry_button.winfo_ismapped())
    x.withdraw()
    x.destroy()


# ══ Previews (real ImageMagick) ═══════════════════════════════════════════════════

@test("previews", gui=False)
def _():
    if not HAS_MAGICK:
        SKIPPED.append("previews (ImageMagick not found)")
        return
    src = src_dir("real")
    subprocess.run(["magick", "-size", "900x600", "gradient:red-blue", str(src / "real.jpg")], check=True)
    write_record("data/runs/2026-09-21.json", _run("2026-09-21", photos=a.copy_photos(src, "2026-09-21")))
    a.write_data_js()
    rel = "data/photos/2026-09-21/real.jpg"
    before = mp.read_dims()
    quiet(mp.main, [])
    dims = mp.read_dims()
    check("previews are encoded for every tier",
          all((SANDBOX / "data/previews" / t / "2026-09-21/real.webp").exists() for t in ("micro", "thumb", "card")))
    check("the new image is measured", dims.get(rel) == [900, 600], dims.get(rel))
    check("sizes already known are reused", all(dims.get(k) == v for k, v in before.items() if k in dims))
    m = (SANDBOX / "data/photo-dims.js").stat().st_mtime_ns
    quiet(mp.main, [])
    check("a second pass leaves photo-dims.js alone", (SANDBOX / "data/photo-dims.js").stat().st_mtime_ns == m)
    dims_path = SANDBOX / "data/photo-dims.js"
    dims_path.write_bytes(dims_path.read_text("utf-8").encode("utf-16"))
    quiet(mp.main, [])
    check("a photo-dims.js re-saved as UTF-16 is rewritten", dims_path.read_bytes().startswith(b"//"))


# ══ Feed with no runs (last, as it deletes every run) ═════════════════════════════

@test("empty feed")
def _():
    quiet(mf.main, [])
    check("the feed has entries before", (SANDBOX / "atom.xml").read_text("utf-8").count("<entry>") > 3)
    for p in list((SANDBOX / "data/runs").glob("*.json")):
        select_run(p.stem)._delete()
    rc = quiet(mf.main, [])
    xml = (SANDBOX / "atom.xml").read_text("utf-8")
    check("deleting the last run empties the feed", rc == 0 and xml.count("<entry>") == 0 and "RUNS_DATA" not in xml, rc)
    quiet(mf.main, [])
    check("regenerating an empty feed gives the same file", (SANDBOX / "atom.xml").read_text("utf-8") == xml)
    rc = quiet(mp.main, [])
    check("photo-dims.js is emptied too", rc == 0 and "data/photos" not in (SANDBOX / "data/photo-dims.js").read_text("utf-8"))
    (SANDBOX / "data/data.js").rename(SANDBOX / "data/data.js.bak")
    try:
        rc = quiet(mf.main, [])
        check("a missing data.js is an error and keeps the old feed",
              rc == 1 and (SANDBOX / "atom.xml").read_text("utf-8") == xml)
        check("the editor reports it", quiet(a.refresh_feed) is not None)
    finally:
        (SANDBOX / "data/data.js.bak").rename(SANDBOX / "data/data.js")


# ══ The real data: every record opens and saves back unchanged ════════════════════

@test("real data")
def _():
    real = TMP / "real"
    real.mkdir()
    for f in SCRIPTS:
        shutil.copy2(REPO / f, real / f)
    for d in ("runs", "pbs"):
        shutil.copytree(REPO / "data" / d, real / "data" / d)
    code = textwrap.dedent("""
        import json, sys
        from pathlib import Path
        sys.path.insert(0, ".")
        # Line endings aside: a checkout may hold the JSON with LF or CRLF, the editor
        # writes the platform's, and git's text=auto makes those the same file.
        def body(path):
            return path.read_bytes().replace(b"\\r\\n", b"\\n")
        orig = {f"{d}/{p.name}": body(p) for d in ("runs", "pbs") for p in Path("data", d).glob("*.json")}
        import add_new_event as a
        log = []
        for n in ("showinfo", "showerror", "showwarning", "askyesno"):
            setattr(a.messagebox, n, lambda t, m, n=n, **k: log.append(n) or True)
        a.messagebox.askretrycancel = lambda t, m, **k: log.append("askretrycancel") or False
        a.BackgroundRefresh.__init__.__defaults__ = (lambda: None,)
        app = a.App(); app.withdraw()
        out = {"problems": a.load_problems(), "count": 0, "changed": [],
               "startup_changed": [k for k, b in orig.items() if body(Path("data", k)) != b]}
        for tab, items in ((app.edit_run_tab, "runs"), (app.edit_pb_tab, "pbs")):
            tab.refresh()
            for i in range(len(getattr(tab, items))):
                tab.refresh()
                rec = getattr(tab, items)[i]
                key = f"{items}/{rec['_path'].name}"
                tab.listbox.selection_set(i); tab._on_select(None); tab._save()
                out["count"] += 1
                if body(rec["_path"]) != orig.get(key) or log[-1] != "showinfo":
                    out["changed"].append(key)
        print(json.dumps(out))
    """)
    r = subprocess.run([sys.executable, "-c", code], cwd=real, capture_output=True, env=CHILD_ENV,
                       encoding="utf-8", errors="replace", timeout=300)
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        check("real data round trip", False, r.stdout[-500:] + r.stderr[-1500:])
        return
    check(f"all {out['count']} real records load, survive the editor starting, and save back unchanged",
          not out["problems"] and not out["startup_changed"] and not out["changed"] and out["count"] > 0, out)


# Tk objects must be freed on the main thread. An App that became garbage mid-run could
# be collected by a background pass's thread instead, which aborts the process — the
# editor itself only ever has the one App, referenced until it exits.
for x in APPS + [app] * (app is not None):
    try:
        x.destroy()
    except a.tk.TclError:
        pass                     # already destroyed by its test
APPS.clear()
gui_missing = app is None
app = None
gc.collect()
os.chdir(REPO)
shutil.rmtree(TMP, ignore_errors=True)
fails = [r for r in RESULTS if not r[1]]
for name, ok, detail in fails:
    print("FAIL", name, "\n     ", str(detail)[:1500])
for name in SKIPPED:
    print("SKIP", name, "" if "ImageMagick" in name else f"(no usable Tk: {NO_TK})")
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed"
      + (f", {len(SKIPPED)} group(s) skipped" if SKIPPED else ""))
if REQUIRE_GUI and gui_missing:
    print("FAIL --require-gui: Tk is not available, so the GUI groups did not run")
    sys.exit(2)
sys.exit(1 if fails else 0)
