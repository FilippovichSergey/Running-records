"""
The .bat launchers: each must run its script from the launcher's own folder, whatever
drive and folder it is started from, including a folder whose name has spaces, and
pass the script's exit code on.

    python tests/test_launchers.py

make_feed.bat and make_previews.bat are really run, from a copy of the project in a temp
folder named with spaces, with the current folder on another drive when the machine
has one, and with options that write nothing (--check / --dry-run). Then every launcher,
including run.bat and the importers, is run against stand-in scripts that only report
the folder they were started in, the arguments they got, and exit with a chosen code, so
nothing opens a window, goes online or touches data. Windows only; the real project
folder is never written to.
"""

import json
import os
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if sys.platform != "win32":
    print("skipped: the .bat launchers only run on Windows")
    sys.exit(0)

LAUNCHERS = {
    "run.bat": "python add_new_event.py",
    "make_feed.bat": "python make_feed.py %*",
    "make_previews.bat": "python make_previews.py %*",
    "process_activities.bat": "python process_activities.py",
    "fetch_strava.bat": "python fetch_strava.py %*",
    "fetch_garmin.bat": "python fetch_garmin.py %*",
}
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


# ── Every launcher: the same safe lines ─────────────────────────────────────────
for name, command in LAUNCHERS.items():
    lines = [l.strip() for l in (REPO / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    check(f"{name} switches to its own folder and drive first",
          'cd /d "%~dp0" || exit /b 1' in lines and lines.index('cd /d "%~dp0" || exit /b 1') < lines.index(command),
          lines)
    check(f"{name} runs {command.split()[1]}, which exists", command in lines and (REPO / command.split()[1]).exists())
    check(f"{name} passes the exit code on", 'set "rc=%errorlevel%"' in lines and lines[-1] == "exit /b %rc%", lines)
    check(f"{name} has no hard-coded project path", "running_records" not in " ".join(lines).lower(), lines)


# ── make_feed.bat / make_previews.bat for real ─────────────────────────────────
TMP = Path(tempfile.mkdtemp(prefix="running_log_launchers_"))
copy = TMP / "Running records copy"          # a folder name with spaces
(copy / "data").mkdir(parents=True)
for f in ("make_feed.py", "make_previews.py", "make_feed.bat", "make_previews.bat"):
    shutil.copy2(REPO / f, copy / f)
(copy / "data/data.js").write_text("const RUNS_DATA = [];\n\nconst PBS_DATA = [];\n", "utf-8")

# Start from another drive if there is one: `cd` without /d would stay on it.
copy_drive = copy.drive.upper()
others = [f"{d}:\\" for d in string.ascii_uppercase if f"{d}:" != copy_drive and Path(f"{d}:\\").is_dir()]
start = Path(others[0]) if others else Path(tempfile.gettempdir())
where = f"from {start} (another drive)" if others else f"from {start} (no other drive on this machine)"


def launch(bat: Path, *args, env=None):
    # cmd /s /c "…": keep the quotes around a path with spaces; "\n" answers `pause`.
    line = f'cmd /s /c ""{bat}" {" ".join(args)}"'
    r = subprocess.run(line, cwd=start, input="\n", capture_output=True, text=True, timeout=120, env=env)
    return r.returncode, r.stdout + r.stderr


rc, out = launch(copy / "make_feed.bat", "--check")
check(f"make_feed.bat runs {where}, from a folder with spaces",
      rc == 0 and "Would write atom.xml: 0 entries" in out, out[-600:])
check("make_feed.bat --check wrote nothing", not (copy / "atom.xml").exists())
rc, out = launch(copy / "make_previews.bat", "--dry-run")
check(f"make_previews.bat runs {where}", rc == 0 and "No image paths found" in out, out[-600:])
check("make_previews.bat --dry-run wrote nothing", not (copy / "data/photo-dims.js").exists())
(copy / "data/data.js").unlink()
rc, out = launch(copy / "make_feed.bat", "--check")
check("make_feed.bat passes a failing exit code on", rc == 1 and "could not read RUNS_DATA" in out, (rc, out[-400:]))

# Control: the old form (plain cd to a fixed path) must fail here when there is
# another drive, so the checks above can tell a working launcher from a broken one.
if others:
    old = copy / "old_make_feed.bat"
    old.write_text(f"cd {copy}\\\npython make_feed.py %*\n", encoding="utf-8")
    (copy / "data/data.js").write_text("const RUNS_DATA = [];\n\nconst PBS_DATA = [];\n", "utf-8")
    rc, out = launch(old, "--check")
    check("control: a launcher without /d fails from another drive", "Would write atom.xml" not in out, out[-400:])

# ── Every launcher, against stand-in scripts ────────────────────────────────────
STUB = """import json, os, sys
print("STUB " + json.dumps({"cwd": os.getcwd(), "args": sys.argv[1:]}))
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""
stubs = TMP / "Stand-in copy with spaces"
stubs.mkdir()
for name, command in LAUNCHERS.items():
    shutil.copy2(REPO / name, stubs / name)
    (stubs / command.split()[1]).write_text(STUB, encoding="utf-8")


def stub_report(out):
    line = next((l for l in out.splitlines() if l.startswith("STUB ")), None)
    return json.loads(line[5:]) if line else None


for name, command in LAUNCHERS.items():
    rc, out = launch(stubs / name, "--flag", '"two words"')
    got = stub_report(out)
    same_dir = got is not None and os.path.normcase(os.path.realpath(got["cwd"])) == os.path.normcase(os.path.realpath(stubs))
    check(f"{name} runs its script in its own folder {where}", rc == 0 and same_dir, (rc, out[-400:]))
    expected = ["--flag", "two words"] if "%*" in command else []
    check(f"{name} passes {'its arguments on' if expected else 'no arguments (the script takes none)'}",
          got is not None and got["args"] == expected, got)
    rc, out = launch(stubs / name, env={**os.environ, "STUB_EXIT": "3"})
    check(f"{name} returns the script's exit code", rc == 3 and stub_report(out) is not None, (rc, out[-300:]))

shutil.rmtree(TMP, ignore_errors=True)
fails = [r for r in RESULTS if not r[1]]
for name, ok, detail in fails:
    print("FAIL", name, "\n     ", str(detail)[:800])
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed ({where})")
sys.exit(1 if fails else 0)
