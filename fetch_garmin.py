"""
Fetch running activities from Garmin Connect and write data/activities.js.

First-time setup
----------------
1. Install the dependency:
       pip install garminconnect
2. Run the script:
       python fetch_garmin.py
   You will be prompted for your Garmin email and password.
   If your account uses MFA, you will also be prompted for the one-time code.
   Credentials and OAuth tokens are saved to .garmin_tokens/ so subsequent
   runs log in silently — no password re-entry needed.

Usage
-----
    python fetch_garmin.py              # fetch all activities
    python fetch_garmin.py --days 90    # only last N days
    python fetch_garmin.py --merge      # merge with existing activities.js
    python fetch_garmin.py --reauth     # force re-login (e.g. after password change)

Dependencies
------------
    pip install garminconnect
"""

import argparse
import getpass
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from garminconnect import (
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    )
except ImportError:
    sys.exit("Install garminconnect first:  pip install garminconnect")

BASE_DIR    = Path(__file__).parent
TOKEN_DIR   = BASE_DIR / ".garmin_tokens"
OUTPUT_JS   = BASE_DIR / "data" / "activities.js"
CREDS_FILE  = BASE_DIR / "garmin_credentials.json"

RUNNING_TYPE_KEYS = {
    "running", "trail_running", "track_running", "indoor_running",
    "treadmill_running", "virtual_run", "ultra_running",
    "obstacle_run", "street_running",
}

TYPE_LABELS = {
    "running":          "Running",
    "trail_running":    "Trail Running",
    "track_running":    "Track Running",
    "indoor_running":   "Indoor Running",
    "treadmill_running":"Treadmill Running",
    "virtual_run":      "Virtual Running",
    "ultra_running":    "Ultra Running",
    "obstacle_run":     "Obstacle Course Racing",
    "street_running":   "Street Running",
}


# ── Authentication ────────────────────────────────────────────────────────────

def load_credentials() -> tuple[str, str]:
    if CREDS_FILE.exists():
        data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
        return data["email"], data["password"]
    print("Garmin Connect credentials (saved locally to garmin_credentials.json):")
    email    = input("Email:    ").strip()
    password = getpass.getpass("Password: ")
    CREDS_FILE.write_text(
        json.dumps({"email": email, "password": password}, indent=2),
        encoding="utf-8",
    )
    return email, password


def get_client(reauth: bool = False) -> Garmin:
    email, password = load_credentials()
    api = Garmin(email=email, password=password, is_cn=False)

    token_store = str(TOKEN_DIR)
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)

    if reauth or not any(TOKEN_DIR.iterdir() if TOKEN_DIR.exists() else []):
        print("Logging in to Garmin Connect…")
        try:
            api.login()
        except GarminConnectAuthenticationError:
            # MFA prompt
            mfa = input("Enter MFA / one-time code: ").strip()
            api.login(mfa_code=mfa)
        api.garth.dump(token_store)
        print("Login successful. Tokens saved.\n")
    else:
        try:
            api.login(token_store)
        except Exception:
            print("Stored token invalid — re-logging in…")
            try:
                api.login()
            except GarminConnectAuthenticationError:
                mfa = input("Enter MFA / one-time code: ").strip()
                api.login(mfa_code=mfa)
            api.garth.dump(token_store)
            print("Re-login successful.\n")
    return api


# ── Fetch activities ──────────────────────────────────────────────────────────

def fetch_all(api: Garmin, after_date: datetime | None = None) -> list[dict]:
    activities = []
    start      = 0
    limit      = 100
    while True:
        try:
            batch = api.get_activities(start, limit)
        except GarminConnectTooManyRequestsError:
            import time
            print("Rate limited — waiting 60s…")
            time.sleep(60)
            batch = api.get_activities(start, limit)

        if not batch:
            break

        if after_date:
            filtered = []
            done = False
            for a in batch:
                dt_str = a.get("startTimeLocal", "")
                if not dt_str:
                    continue
                dt = datetime.fromisoformat(dt_str)
                if dt < after_date:
                    done = True
                    break
                filtered.append(a)
            activities.extend(filtered)
            if done:
                break
        else:
            activities.extend(batch)

        print(f"  Fetched {start + len(batch)} activities so far…")
        if len(batch) < limit:
            break
        start += limit

    return activities


def garmin_to_record(a: dict) -> dict | None:
    type_key = (a.get("activityType") or {}).get("typeKey", "")
    if type_key not in RUNNING_TYPE_KEYS:
        return None

    dt_str = a.get("startTimeLocal", "")
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)

    dist_m   = a.get("distance") or 0
    dist_km  = round(dist_m / 1000, 2)
    elev     = max(0, int(a.get("elevationGain") or 0))
    seconds  = int(a.get("duration") or 0)
    h, rem   = divmod(seconds, 3600)
    m, s     = divmod(rem, 60)
    time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    return {
        "type":        TYPE_LABELS.get(type_key, type_key),
        "date":        dt.strftime("%Y-%m-%d"),
        "datetime":    dt.strftime("%Y-%m-%d %H:%M:%S"),
        "distance_km": dist_km,
        "time":        time_str,
        "elevation":   elev,
    }


# ── Output ────────────────────────────────────────────────────────────────────

def load_existing() -> dict[str, dict]:
    if not OUTPUT_JS.exists():
        return {}
    text  = OUTPUT_JS.read_text(encoding="utf-8")
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start == -1 or end == 0:
        return {}
    try:
        return {r["datetime"]: r for r in json.loads(text[start:end])}
    except json.JSONDecodeError:
        return {}


def write_js(records: list[dict]):
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    js = (
        "// Auto-generated by fetch_garmin.py — do not edit manually\n"
        f"const ACTIVITIES_DATA = {json.dumps(records, ensure_ascii=False, indent=2)};\n"
    )
    OUTPUT_JS.write_text(js, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch Garmin activities → data/activities.js")
    parser.add_argument("--days",   type=int,  default=None,
                        help="Only fetch activities from the last N days (default: all)")
    parser.add_argument("--merge",  action="store_true",
                        help="Merge with existing activities.js (default: replace)")
    parser.add_argument("--reauth", action="store_true",
                        help="Force re-login even if stored tokens exist")
    args = parser.parse_args()

    api = get_client(reauth=args.reauth)

    after_date = None
    if args.days:
        after_date = datetime.now() - timedelta(days=args.days)
        print(f"Fetching activities from last {args.days} days…")
    else:
        print("Fetching all activities…")

    raw = fetch_all(api, after_date=after_date)
    print(f"Total fetched from Garmin: {len(raw)}")

    new_records: dict[str, dict] = {}
    for a in raw:
        rec = garmin_to_record(a)
        if rec:
            new_records[rec["datetime"]] = rec

    if args.merge:
        existing = load_existing()
        existing.update(new_records)
        merged = existing
    else:
        merged = new_records

    result = sorted(merged.values(), key=lambda r: r["datetime"], reverse=True)
    write_js(result)

    print(f"Running activities fetched: {len(new_records)}")
    print(f"Total in activities.js:     {len(result)}")
    print(f"Output: {OUTPUT_JS}")


if __name__ == "__main__":
    main()
