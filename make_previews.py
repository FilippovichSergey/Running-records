"""
Generate small WebP preview images for the dashboard.

The site displays photos in tiny slots (64px medal circles, 140-170px grid/strip
cells) but was serving the full-size originals — several hundred KB to tens of MB
each. This script renders a small preview per tier; the lightbox keeps opening the
untouched original.

Which images? Exactly the paths referenced by data/data.js, so coverage is 1:1
with what the site actually loads and no preview can be missing.

Destination mapping (the "resized/" segment is preserved, which makes the map
structurally 1:1 — no two sources can collide):

    data/photos/resized/2024-06-08/DSC_4258.jpg
        -> data/previews/<tier>/resized/2024-06-08/DSC_4258.webp
    data/photos/2026-08-09/medal.jpg
        -> data/previews/<tier>/2026-08-09/medal.webp

Directory and file-stem CASE IS PRESERVED (only the extension is lowercased).
Vercel's filesystem is case-sensitive while Windows is not, so normalising case
here would 404 in production only.

Usage:
    python make_previews.py                # generate what is missing/stale
    python make_previews.py --force        # re-encode everything
    python make_previews.py --dry-run      # show the plan, write nothing
    python make_previews.py --prune        # also delete previews with no reference
    python make_previews.py --jobs 4       # limit parallelism

Requires ImageMagick 7 ("magick" on PATH).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_DIR     = Path(__file__).parent
DATA_JS      = BASE_DIR / "data" / "data.js"
PREVIEW_ROOT = BASE_DIR / "data" / "previews"
DIMS_JS      = BASE_DIR / "data" / "photo-dims.js"
SRC_PREFIX   = "data/photos/"

# tier -> (width cap in px, WebP quality)
#   micro 256 : 64px medal badges at DPR3 (256 wide keeps height >= 192 even at 4:3)
#   thumb 640 : small Overview cells, strip cells 2-3, Personal Bests grid
#   card 1280 : big Overview cell, first strip cell, Overview hero
TIERS = {
    "micro": (256, 85),
    "thumb": (640, 80),
    "card":  (1280, 80),
}

PATH_RE = re.compile(r'"(data/photos/[^"]+)"')

# Hide the console window ImageMagick would otherwise flash over the Tk GUI.
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def referenced_paths() -> list[str]:
    """Every data/photos/... path referenced by data.js, unique and sorted."""
    if not DATA_JS.exists():
        return []
    text = DATA_JS.read_text(encoding="utf-8-sig")
    return sorted(set(PATH_RE.findall(text)))


def dest_for(src_rel: str, tier: str) -> Path:
    """Map a referenced path to its preview path for the given tier."""
    rel = src_rel[len(SRC_PREFIX):]           # keep any "resized/" segment
    rel = re.sub(r"\.[^./]+$", "", rel)       # [^./] so "pb_21.1_км/x" keeps its dot
    return PREVIEW_ROOT / tier / (rel + ".webp")


def convert(src: Path, dest: Path, width: int, quality: int) -> tuple[bool, str]:
    """Encode one preview. Returns (ok, message)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.webp")
    cmd = [
        "magick", str(src),
        "-auto-orient",                       # must precede -strip, or EXIF rotation is lost
        "-resize", f"{width}x>",              # width cap, shrink-only ('>' never enlarges)
        "-background", "white",               # composite any alpha before a lossy encode
        "-alpha", "remove",
        "-alpha", "off",
        "-strip",
        "-colorspace", "sRGB",
        "-define", "webp:method=6",
        "-quality", str(quality),
        str(tmp),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           creationflags=_CREATE_NO_WINDOW)
    except FileNotFoundError:
        return False, "ImageMagick not found — install it and ensure 'magick' is on PATH"
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        return False, (r.stderr or "magick failed").strip().splitlines()[-1][:200]
    os.replace(tmp, dest)                      # atomic: never leaves a truncated file
    return True, ""


def write_dims(paths):
    """Write data/photo-dims.js — the natural size of every referenced image.

    The dashboard sets width/height on each <img> from this, so a cell can take
    its photo's own aspect ratio with no layout shift before the image loads.
    """
    dims = {}
    for rel in paths:
        src = BASE_DIR / rel
        if not src.exists():
            continue
        try:
            r = subprocess.run(
                ["magick", "identify", "-format", "%w %h", str(src) + "[0]"],
                capture_output=True, text=True, creationflags=_CREATE_NO_WINDOW)
            w, h = r.stdout.strip().split()
            dims[rel] = [int(w), int(h)]
        except Exception:
            pass   # a missing entry just falls back to the browser's natural sizing
    nl = chr(10)
    body = ("," + nl).join(
        "  %s: [%d,%d]" % (json.dumps(k), v[0], v[1]) for k, v in sorted(dims.items()))
    DIMS_JS.write_text(
        "// Auto-generated by make_previews.py — do not edit manually" + nl +
        "const PHOTO_DIMS = {" + nl + body + nl + "};" + nl,
        encoding="utf-8")
    return len(dims)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate WebP previews for the dashboard.")
    ap.add_argument("--force",   action="store_true", help="re-encode even if up to date")
    ap.add_argument("--dry-run", action="store_true", help="show the plan, write nothing")
    ap.add_argument("--prune",   action="store_true", help="delete previews with no reference")
    ap.add_argument("--jobs",    type=int, default=min(8, os.cpu_count() or 4))
    args = ap.parse_args(argv)

    paths = referenced_paths()
    if not paths:
        print(f"No image paths found in {DATA_JS} — nothing to do.")
        return 0

    # Build the job list, refusing collisions rather than silently overwriting.
    jobs, claimed, missing = [], {}, []
    for rel in paths:
        src = BASE_DIR / rel
        if not src.exists():
            missing.append(rel)
            continue
        for tier, (width, quality) in TIERS.items():
            dest = dest_for(rel, tier)
            if dest in claimed and claimed[dest] != rel:
                print(f"ERROR: {rel} and {claimed[dest]} both map to {dest}")
                return 1
            claimed[dest] = rel
            fresh = dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime
            if args.force or not fresh:
                jobs.append((src, dest, width, quality))

    for rel in missing:
        print(f"WARNING: referenced but not on disk — {rel}")

    print(f"{len(paths)} referenced image(s) x {len(TIERS)} tier(s); "
          f"{len(jobs)} to encode, {len(paths) * len(TIERS) - len(jobs) - len(missing) * len(TIERS)} up to date")

    if args.dry_run:
        for src, dest, w, q in jobs[:20]:
            print(f"  would write {dest.relative_to(BASE_DIR)}  ({w}px q{q})")
        if len(jobs) > 20:
            print(f"  … and {len(jobs) - 20} more")
        return 0

    ok = fail = 0
    if jobs:
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            for (src, dest, _, _), (good, msg) in zip(
                jobs, pool.map(lambda j: convert(*j), jobs)
            ):
                if good:
                    ok += 1
                else:
                    fail += 1
                    print(f"  FAILED {src.name}: {msg}")
        print(f"Encoded {ok}, failed {fail}")

    if args.prune:
        wanted = set(claimed)
        removed = 0
        for f in PREVIEW_ROOT.rglob("*.webp"):
            if f not in wanted:
                f.unlink()
                removed += 1
        for d in sorted(PREVIEW_ROOT.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        print(f"Pruned {removed} orphaned preview(s)")

    n_dims = write_dims(paths)
    print(f"Wrote {DIMS_JS.name} with {n_dims} image dimension(s)")

    if PREVIEW_ROOT.exists():
        files = list(PREVIEW_ROOT.rglob("*.webp"))
        total = sum(f.stat().st_size for f in files)
        print(f"Previews: {len(files)} files, {human(total)} in {PREVIEW_ROOT.relative_to(BASE_DIR)}")

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
