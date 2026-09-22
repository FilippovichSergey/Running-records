"""
Closing the editor while previews are still being generated (real ImageMagick).

    python tests/test_close.py
    python tests/test_close.py --require-gui      # fail, rather than skip, without Tk / ImageMagick

Each scenario runs the real editor in a child process on a throw-away copy of the
scripts, with generated images, so the real data/ folder is never touched. Skipped
when ImageMagick ("magick") is not on PATH or Tk can't start.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Child Pythons write UTF-8 and are read as UTF-8, whatever this machine's code page is
# (GitHub's Windows runners pipe output as cp1252, where Cyrillic can't be encoded).
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
sys.stdout.reconfigure(errors="backslashreplace")     # our own prints never crash on it
# A skip exits 0; with --require-gui it exits 2, so a full check can't pass by skipping.
SKIP_CODE = 2 if "--require-gui" in sys.argv else 0
if shutil.which("magick") is None:
    print("skipped: ImageMagick not found")
    sys.exit(SKIP_CODE)
try:
    import tkinter
    tkinter.Tk().destroy()
except Exception as e:                  # tkinter.TclError: no usable Tcl/Tk here
    print(f"skipped: no usable Tk ({e})")
    sys.exit(SKIP_CODE)

TMP = Path(tempfile.mkdtemp(prefix="running_log_close_"))
IMAGES = ["a.jpg", "b.jpg", "c.jpg"]
RESULTS = []

for i, name in enumerate(IMAGES):
    subprocess.run(["magick", "-size", "800x600", f"gradient:red-{('blue', 'green', 'white')[i]}",
                    str(TMP / name)], check=True)


def sandbox(label):
    sb = TMP / label
    for f in ("add_new_event.py", "make_previews.py", "make_feed.py"):
        (sb).mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / f, sb / f)
    for d in ("runs", "pbs", "photos/x"):
        (sb / "data" / d).mkdir(parents=True, exist_ok=True)
    for name in IMAGES:
        shutil.copy2(TMP / name, sb / "data/photos/x" / name)
    return sb


def run_json(date, images):
    return {"date": date, "race_name": date, "location": "X", "distance_km": 10.0,
            "total_time": "45:00", "photos": [f"data/photos/x/{n}" for n in images], "medal": ""}


def run_child(sb, code):
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=sb, env=CHILD_ENV,
                       capture_output=True, encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, r.stdout + r.stderr


# ── 1: a pass queued when the window closes still runs, and runs completely ──────
sb = sandbox("queued")
(sb / "data/runs/2026-01-01.json").write_text(json.dumps(run_json("2026-01-01", IMAGES[:1])), "utf-8")
second = json.dumps(run_json("2026-01-02", IMAGES[1:]))
code, out = run_child(sb, f"""
    import sys, time; sys.path.insert(0, ".")
    import make_previews
    real_convert = make_previews.convert
    def slow_convert(*args):                 # make each pass last long enough to close during it
        time.sleep(0.6)
        return real_convert(*args)
    make_previews.convert = slow_convert
    import add_new_event as a
    app = a.App()                            # startup starts pass 1
    print("pass1 busy:", app.refresher.busy, flush=True)
    def second_save_then_close():
        (a.RUNS_DIR / "2026-01-02.json").write_text({second!r}, "utf-8")
        a.write_data_js(); app.start_refresh()      # folded into pass 2
        app._on_close()                             # the user closes the window
        print("closed; withdrawn:", app.state() == "withdrawn", flush=True)
    app.after(200, second_save_then_close)
    app.mainloop()
    print("mainloop returned; busy:", app.refresher.busy, flush=True)
""")
dims_file = sb / "data/photo-dims.js"
dims = dims_file.read_text("utf-8") if dims_file.exists() else ""
atom = (sb / "atom.xml").read_text("utf-8") if (sb / "atom.xml").exists() else ""
RESULTS += [
    ("exits with code 0", code == 0, out[-800:]),
    ("pass 1 was running when the window closed", "pass1 busy: True" in out, out[-800:]),
    ("the window hides instead of closing while busy", "closed; withdrawn: True" in out, out[-800:]),
    ("mainloop returns only when idle", "mainloop returned; busy: False" in out, out[-800:]),
    ("no 'cannot schedule new futures'", "cannot schedule" not in out and "not generated" not in out, out[-800:]),
    ("previews for both saves, every tier",
     all((sb / "data/previews" / t / "x" / (Path(n).stem + ".webp")).exists()
         for t in ("micro", "thumb", "card") for n in IMAGES), out[-800:]),
    ("photo-dims.js has all three images", all(n in dims for n in IMAGES), dims[:300]),
    ("atom.xml has both runs", atom.count("<entry>") == 2, atom[:200]),
    ("no temp files left", not list(sb.rglob("*.tmp")) and not list(sb.rglob("*.tmp.webp"))),
]

# ── 2: garbage collection on the worker thread after closing must not abort ─────
GC_CHILD = """
    import gc, sys, time; sys.path.insert(0, ".")
    import add_new_event as a
    def work():
        time.sleep(1.0)
        gc.collect()            # a full collection that happens to run on the worker thread
        print("worker survived gc", flush=True)
    a.BackgroundRefresh.__init__.__defaults__ = (work,)
    {setup}
"""
FIXED = """
    app = a.App()
    app.after(100, app._on_close)
    app.mainloop()
    print("main done", flush=True)
"""
OLD = """
    a.App._on_close = lambda self: self.destroy()     # what closing used to do
    app = a.App()
    app.after(100, app._on_close)
    del app                                           # previously: App().mainloop(), no reference
    import tkinter
    tkinter._default_root.mainloop()
    print("main done", flush=True)
"""
for label, setup in (("fixed", FIXED), ("old", OLD)):
    sb = sandbox("gc_" + label)
    code, out = run_child(sb, GC_CHILD.replace("{setup}", textwrap.indent(textwrap.dedent(setup), "    ").strip()))
    clean = code == 0 and "worker survived gc" in out and "main done" in out and "Tcl_AsyncDelete" not in out
    if label == "fixed":
        RESULTS.append(("closing during a pass exits cleanly", clean, f"code={code}\n{out[-800:]}"))
    else:
        RESULTS.append(("control: the old way of closing still crashes here (so the test can tell)",
                        not clean, f"code={code}\n{out[-400:]}"))

shutil.rmtree(TMP, ignore_errors=True)
fails = [r for r in RESULTS if not r[1]]
for name, ok, *detail in RESULTS:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "\n      " + str(detail[0] if detail else "")))
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
sys.exit(1 if fails else 0)
