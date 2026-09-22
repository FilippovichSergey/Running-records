"""
Run every test suite and print one summary: which version was tested, what ran, what
passed and what was skipped.

    python tests/run_all.py                  # skips allowed (e.g. no Tk on this machine)
    python tests/run_all.py --require-gui    # a skipped GUI check fails the run

A bare "passed" count says little when the GUI checks could not run, so the summary
always lists skips next to it. On GitHub Actions the same table is added to the run's
summary page, where it stays attached to the commit.

Exit code: 0 when every suite passed, otherwise the first suite's non-zero code.
"""

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
REQUIRE_GUI = "--require-gui" in sys.argv

# file, whether it understands --require-gui
SUITES = [("test_editor.py", True), ("test_close.py", True), ("test_launchers.py", False)]


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                              timeout=30).stdout.strip() or "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def tk_status():
    try:
        import tkinter
        tkinter.Tk().destroy()
        return "yes"
    except Exception as e:                     # TclError: no usable Tcl/Tk
        return f"no ({e})"


def summary_of(out: str) -> tuple[str, str]:
    """(result line, skips) from a suite's output."""
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    result = next((l for l in reversed(lines) if re.search(r"\d+/\d+ passed", l)), "")
    skipped = [l for l in lines if l.startswith(("SKIP", "skipped:"))]
    if not result and skipped:
        result = "skipped"
    return result or (lines[-1] if lines else "no output"), f"{len(skipped)} skip line(s)" if skipped else "none"


def main() -> int:
    head = git("rev-parse", "--short", "HEAD")
    dirty = " (with uncommitted changes)" if git("status", "--porcelain", "--untracked-files=no") != "?" else ""
    env = [f"commit {head}{dirty}", f"Python {platform.python_version()}", f"Tk: {tk_status()}",
           f"ImageMagick: {'yes' if shutil.which('magick') else 'no'}",
           f"mode: {'--require-gui' if REQUIRE_GUI else 'skips allowed'}"]
    print("Running the test suites — " + ", ".join(env) + "\n")

    rows, first_failure = [], 0
    for name, takes_flag in SUITES:
        cmd = [sys.executable, "-B", str(TESTS / name)] + (["--require-gui"] if REQUIRE_GUI and takes_flag else [])
        try:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=1200)
            code, out = r.returncode, r.stdout + r.stderr
        except subprocess.TimeoutExpired as e:
            code, out = 124, f"timed out after {e.timeout}s"
        result, skips = summary_of(out)
        rows.append((name, code, result, skips))
        if code:
            first_failure = first_failure or code
            print(f"── {name} failed (exit {code}); its last output:")
            print("\n".join(out.rstrip().splitlines()[-40:]) + "\n")

    width = max(len(n) for n, *_ in rows)
    for name, code, result, skips in rows:
        print(f"{'OK  ' if code == 0 else 'FAIL'} {name:<{width}}  exit {code}  {result}  (skipped: {skips})")
    print(f"\n{'All suites passed' if not first_failure else 'Some suites failed'} — " + ", ".join(env))

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("### Test suites\n\n" + " · ".join(env) + "\n\n| Suite | Exit | Result | Skipped |\n|---|---|---|---|\n")
            for name, code, result, skips in rows:
                f.write(f"| `{name}` | {code} | {result} | {skips} |\n")
    return first_failure


if __name__ == "__main__":
    sys.exit(main())
