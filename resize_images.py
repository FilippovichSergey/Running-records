"""
Batch image resizer using ImageMagick 7.
Usage:
    python resize_images.py <input> [options]

    <input>  File or folder. If a folder, all .jpg/.jpeg/.png/.webp inside are processed.

Options:
    --max-size  N     Longest side in pixels (default: 1920)
    --quality   N     JPEG quality 1-100 (default: 85)
    --out       DIR   Output directory. Defaults to <input_folder>/resized/
                      Use --out . to overwrite originals in place.
    --no-enlarge      Skip images already smaller than --max-size (default: on)
    --enlarge         Upscale images smaller than --max-size

Examples:
    python resize_images.py data/photos
    python resize_images.py data/photos --max-size 2560 --quality 90
    python resize_images.py photo.jpg --out .
    python resize_images.py data/photos --out data/photos/resized --max-size 1200
"""

import argparse
import subprocess
import sys
from pathlib import Path

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def find_images(src: Path) -> list[Path]:
    if src.is_file():
        return [src] if src.suffix.lower() in SUPPORTED else []
    return sorted(p for p in src.rglob("*") if p.suffix.lower() in SUPPORTED)


def resolve_out(src: Path, out_arg: str | None) -> Path:
    if out_arg == ".":
        return src if src.is_dir() else src.parent
    if out_arg:
        return Path(out_arg)
    base = src if src.is_dir() else src.parent
    return base / "resized"


def out_path(img: Path, src_root: Path, out_dir: Path, overwrite: bool) -> Path:
    if overwrite:
        return img
    try:
        rel = img.relative_to(src_root)
    except ValueError:
        rel = Path(img.name)
    dest = out_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def resize(img: Path, dest: Path, max_size: int, quality: int, no_enlarge: bool) -> bool:
    # ImageMagick geometry: NxN> shrinks only (respects aspect ratio)
    # Without > it would also enlarge
    geometry = f"{max_size}x{max_size}{'>' if no_enlarge else ''}"
    cmd = [
        "magick",
        str(img),
        "-resize", geometry,
        "-quality", str(quality),
        "-strip",          # remove EXIF/ICC metadata to reduce file size
        "-auto-orient",    # apply EXIF rotation before stripping
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def human_bytes(path: Path) -> str:
    b = path.stat().st_size
    for unit in ("B", "KB", "MB"):
        if b < 1024:
            return f"{b:.0f} {unit}"
        b /= 1024
    return f"{b:.1f} MB"


def main():
    parser = argparse.ArgumentParser(description="Batch resize images with ImageMagick.")
    parser.add_argument("input", help="File or folder to process")
    parser.add_argument("--max-size",   type=int, default=1920, metavar="N",
                        help="Longest side in pixels (default: 1920)")
    parser.add_argument("--quality",    type=int, default=85, metavar="N",
                        help="JPEG quality (default: 85)")
    parser.add_argument("--out",        metavar="DIR",
                        help="Output directory (default: <input>/resized). Use . to overwrite.")
    parser.add_argument("--enlarge",    action="store_true",
                        help="Upscale images smaller than --max-size")
    args = parser.parse_args()

    src = Path(args.input).resolve()
    if not src.exists():
        sys.exit(f"Error: '{src}' does not exist.")

    images = find_images(src)
    if not images:
        sys.exit("No supported images found.")

    overwrite = args.out == "."
    out_dir = resolve_out(src, args.out)
    if not overwrite:
        out_dir.mkdir(parents=True, exist_ok=True)

    src_root = src if src.is_dir() else src.parent
    no_enlarge = not args.enlarge

    print(f"Resizing {len(images)} image(s)  max={args.max_size}px  quality={args.quality}")
    print(f"Output: {'(in place)' if overwrite else out_dir}\n")

    ok = fail = skipped = 0
    for img in images:
        dest = out_path(img, src_root, out_dir, overwrite)
        before = human_bytes(img)
        if resize(img, dest, args.max_size, args.quality, no_enlarge):
            after = human_bytes(dest)
            print(f"  OK  {img.name:<40} {before:>8} -> {after}")
            ok += 1
        else:
            print(f"  FAIL {img.name}")
            fail += 1

    print(f"\nDone: {ok} resized, {fail} failed, {skipped} skipped.")


if __name__ == "__main__":
    main()
