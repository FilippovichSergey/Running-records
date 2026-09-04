"""
Generate atom.xml — an Atom 1.0 feed of races from data/data.js.

One entry per run, newest first. The feed is a plain static file served from the
site root, so a reader can subscribe to https://<site>/atom.xml.

Usage:
    python make_feed.py            # write atom.xml
    python make_feed.py --check    # print what would be written, write nothing

Run automatically by add_new_event.py after every save.
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

BASE_DIR = Path(__file__).parent
DATA_JS  = BASE_DIR / "data" / "data.js"
OUT      = BASE_DIR / "atom.xml"

SITE     = "https://running-records-lac.vercel.app/"
TITLE    = "Sergey's Running Log"
SUBTITLE = "Race results, personal bests and training stats"
AUTHOR   = "Sergey Filippovich"
# Stable tag: URI authority + date (RFC 4151). Never change these two once published,
# or every entry will look new to subscribers.
TAG_HOST = "running-records-lac.vercel.app"
TAG_DATE = "2022"


def load_runs():
    """Pull RUNS_DATA out of data.js without executing it."""
    if not DATA_JS.exists():
        return []
    text = DATA_JS.read_text(encoding="utf-8-sig")
    m = re.search(r"const RUNS_DATA = (\[.*?\]);", text, re.S)
    return json.loads(m.group(1)) if m else []


def pace(distance_km, total_time):
    """min/km as m:ss, matching calcPace() in app.js."""
    try:
        p = [int(x) for x in total_time.split(":")]
        sec = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
        per = sec / float(distance_km)
        m, s = divmod(int(round(per)), 60)
        return f"{m}:{s:02d}"
    except Exception:
        return ""


def entry_xml(run):
    date = run.get("date", "")
    stamp = f"{date}T00:00:00Z"                       # Atom needs RFC 3339
    name  = run.get("race_name") or run.get("location") or "Run"
    dist  = run.get("distance_km", 0)
    title = f"{name} — {dist} km"

    where = ", ".join(x for x in (run.get("location"), run.get("country")) if x)
    rows = [("Distance", f"{dist} km"), ("Time", run.get("total_time", ""))]
    p = pace(dist, run.get("total_time", ""))
    if p:                       rows.append(("Pace", f"{p} min/km"))
    if run.get("elevation"):    rows.append(("Elevation", f"{run['elevation']} m"))
    if run.get("hr_avg"):       rows.append(("Avg HR", f"{run['hr_avg']} bpm"))
    if where:                   rows.append(("Where", where))
    if run.get("sneakers"):     rows.append(("Shoes", run["sneakers"]))

    body = "".join(f"<li><strong>{escape(k)}:</strong> {escape(str(v))}</li>" for k, v in rows)
    html = f"<ul>{body}</ul>"

    return f"""  <entry>
    <title>{escape(title)}</title>
    <id>tag:{TAG_HOST},{TAG_DATE}:run/{escape(date)}</id>
    <link rel="alternate" type="text/html" href="{escape(SITE)}"/>
    <updated>{stamp}</updated>
    <published>{stamp}</published>
    <summary type="text">{escape(f'{dist} km in {run.get("total_time", "")}' + (f' at {where}' if where else ''))}</summary>
    <content type="html">{escape(html)}</content>
  </entry>"""


def build(runs):
    runs = sorted((r for r in runs if r.get("date")), key=lambda r: r["date"], reverse=True)
    # Feed <updated> comes from the data, not the clock, so regenerating an unchanged
    # log produces a byte-identical file instead of git churn.
    updated = f"{runs[0]['date']}T00:00:00Z" if runs else "1970-01-01T00:00:00Z"
    entries = "\n".join(entry_xml(r) for r in runs)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">
  <title>{escape(TITLE)}</title>
  <subtitle>{escape(SUBTITLE)}</subtitle>
  <id>{escape(SITE)}</id>
  <link rel="alternate" type="text/html" href="{escape(SITE)}"/>
  <link rel="self" type="application/atom+xml" href="{escape(SITE)}atom.xml"/>
  <updated>{updated}</updated>
  <author><name>{escape(AUTHOR)}</name></author>
  <generator uri="{escape(SITE)}">make_feed.py</generator>
{entries}
</feed>
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate atom.xml from data/data.js.")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    runs = load_runs()
    if not runs:
        print(f"No runs found in {DATA_JS} — atom.xml not written.")
        return 0
    xml = build(runs)
    if args.check:
        print(f"Would write {OUT.name}: {len(runs)} entries, {len(xml)} bytes")
        return 0
    # newline="" keeps the exact bytes we built (no CRLF translation on Windows)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(xml)
    print(f"Wrote {OUT.name}: {len(runs)} entries, {len(xml)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
