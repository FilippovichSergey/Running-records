"""
Fetch running activities from Strava and write data/activities.js.

First-time setup
----------------
1. Go to https://www.strava.com/settings/api
2. Create an application (name and website can be anything, e.g. "My Running Log" / "localhost")
3. Copy the Client ID and Client Secret into this script or into a file called
   strava_credentials.json next to this script:
       { "client_id": "12345", "client_secret": "abc..." }
4. Run:  python fetch_strava.py
   A browser window opens → authorize → paste the redirect URL back into the terminal.
   The refresh token is saved to strava_token.json automatically.
   On every subsequent run the token is refreshed silently — no browser needed.

Usage
-----
    python fetch_strava.py            # fetch all activities (up to Strava's history)
    python fetch_strava.py --days 90  # only activities from last N days
    python fetch_strava.py --merge    # merge with existing activities.js instead of replacing

Dependencies
------------
    pip install requests
"""

import argparse
import json
import sys
import time
import webbrowser
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

try:
    import requests
except ImportError:
    sys.exit("Install requests first:  pip install requests")

BASE_DIR       = Path(__file__).parent
TOKEN_FILE     = BASE_DIR / "strava_token.json"
CREDS_FILE     = BASE_DIR / "strava_credentials.json"
OUTPUT_JS      = BASE_DIR / "data" / "activities.js"

AUTH_URL       = "https://www.strava.com/oauth/authorize"
TOKEN_URL      = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
REDIRECT_PORT  = 8765
REDIRECT_URI   = f"http://localhost:{REDIRECT_PORT}/callback"

RUNNING_TYPES = {
    "Run", "TrailRun", "TrackRun", "Treadmill",
    "VirtualRun", "IndoorRun",
}

# Strava type → display name matching process_activities.py conventions
TYPE_LABELS = {
    "Run":        "Running",
    "TrailRun":   "Trail Running",
    "TrackRun":   "Track Running",
    "Treadmill":  "Treadmill Running",
    "VirtualRun": "Virtual Running",
    "IndoorRun":  "Indoor Running",
}


# ── Credentials ──────────────────────────────────────────────────────────────

def load_credentials() -> tuple[str, str]:
    if CREDS_FILE.exists():
        data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
        return str(data["client_id"]), str(data["client_secret"])

    print("\nNo strava_credentials.json found.")
    print("Go to https://www.strava.com/settings/api to create an API application.\n")
    client_id     = input("Client ID:     ").strip()
    client_secret = input("Client Secret: ").strip()
    CREDS_FILE.write_text(
        json.dumps({"client_id": client_id, "client_secret": client_secret}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved to {CREDS_FILE.name}\n")
    return client_id, client_secret


# ── OAuth flow ────────────────────────────────────────────────────────────────

_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = parse_qs(urlparse(self.path).query)
        _auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Authorized! You can close this tab.</h2>")

    def log_message(self, *args):
        pass  # silence request logs


def authorize(client_id: str, client_secret: str) -> dict:
    global _auth_code
    params = {
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope":         "activity:read_all",
    }
    url = AUTH_URL + "?" + urlencode(params)
    print(f"\nOpening browser for Strava authorization…\n{url}\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    print(f"Waiting for authorization (listening on port {REDIRECT_PORT})…")
    while _auth_code is None:
        server.handle_request()
    server.server_close()

    resp = requests.post(TOKEN_URL, data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "code":          _auth_code,
        "grant_type":    "authorization_code",
    })
    resp.raise_for_status()
    token = resp.json()
    TOKEN_FILE.write_text(json.dumps(token, indent=2), encoding="utf-8")
    print("Authorization successful. Token saved.\n")
    return token


def refresh_token(client_id: str, client_secret: str, token: dict) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "grant_type":    "refresh_token",
        "refresh_token": token["refresh_token"],
    })
    resp.raise_for_status()
    new_token = {**token, **resp.json()}
    TOKEN_FILE.write_text(json.dumps(new_token, indent=2), encoding="utf-8")
    return new_token


def get_valid_token(client_id: str, client_secret: str) -> dict:
    if not TOKEN_FILE.exists():
        return authorize(client_id, client_secret)
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    if token.get("expires_at", 0) < time.time() + 60:
        print("Refreshing Strava token…")
        token = refresh_token(client_id, client_secret, token)
    return token


# ── Fetch activities ──────────────────────────────────────────────────────────

def fetch_all(access_token: str, after: int | None = None) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    activities = []
    page = 1
    while True:
        params: dict = {"per_page": 100, "page": page}
        if after:
            params["after"] = after
        resp = requests.get(ACTIVITIES_URL, headers=headers, params=params)
        if resp.status_code == 429:
            wait = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60)) - int(time.time())
            wait = max(wait, 5)
            print(f"Rate limited — waiting {wait}s…")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        activities.extend(batch)
        print(f"  Fetched page {page} ({len(batch)} activities)…")
        page += 1
    return activities


def strava_to_record(a: dict) -> dict | None:
    sport = a.get("sport_type") or a.get("type", "")
    if sport not in RUNNING_TYPES:
        return None
    dt_str = a.get("start_date_local", "")
    if not dt_str:
        return None
    # Parse ISO datetime and format to match existing records
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    date_str     = dt.strftime("%Y-%m-%d")
    datetime_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    dist_km  = round((a.get("distance") or 0) / 1000, 2)
    elev     = max(0, int(a.get("total_elevation_gain") or 0))
    seconds  = int(a.get("moving_time") or 0)
    h, rem   = divmod(seconds, 3600)
    m, s     = divmod(rem, 60)
    time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    return {
        "type":        TYPE_LABELS.get(sport, sport),
        "date":        date_str,
        "datetime":    datetime_str,
        "distance_km": dist_km,
        "time":        time_str,
        "elevation":   elev,
    }


# ── Output ────────────────────────────────────────────────────────────────────

def load_existing() -> dict[str, dict]:
    if not OUTPUT_JS.exists():
        return {}
    text = OUTPUT_JS.read_text(encoding="utf-8")
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start == -1 or end == 0:
        return {}
    try:
        records = json.loads(text[start:end])
        return {r["datetime"]: r for r in records}
    except json.JSONDecodeError:
        return {}


def write_js(records: list[dict]):
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    js = (
        "// Auto-generated by fetch_strava.py — do not edit manually\n"
        f"const ACTIVITIES_DATA = {json.dumps(records, ensure_ascii=False, indent=2)};\n"
    )
    OUTPUT_JS.write_text(js, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch Strava activities → data/activities.js")
    parser.add_argument("--days",  type=int, default=None,
                        help="Only fetch activities from the last N days (default: all)")
    parser.add_argument("--merge", action="store_true",
                        help="Merge with existing activities.js (default: replace)")
    args = parser.parse_args()

    client_id, client_secret = load_credentials()
    token    = get_valid_token(client_id, client_secret)
    access   = token["access_token"]

    after = None
    if args.days:
        after = int((datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp())
        print(f"Fetching activities from last {args.days} days…")
    else:
        print("Fetching all activities…")

    raw = fetch_all(access, after=after)
    print(f"Total fetched from Strava: {len(raw)}")

    new_records: dict[str, dict] = {}
    for a in raw:
        rec = strava_to_record(a)
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

    running_fetched = len(new_records)
    print(f"Running activities fetched: {running_fetched}")
    print(f"Total in activities.js:     {len(result)}")
    print(f"Output: {OUTPUT_JS}")


if __name__ == "__main__":
    main()
