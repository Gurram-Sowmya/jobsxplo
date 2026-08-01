"""
Jobxplo — Stage 6: data processing layer.

Reads data/processed/*.json (from Stage 5, has role_category + raw_title)
and produces the final data/jobs.json matching the Section 5 schema:
  company, raw_title, role_category, experience_level, work_mode,
  location_text, lat, long, date_posted, freshness, job_url

Usage:
    python3 scripts/process_jobs.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
GEOCODE_CACHE_FILE = ROOT / "data" / "geocode_cache.json"
OUTPUT_FILE = ROOT / "data" / "jobs.json"

# ---------- Step 1: experience level ----------

ENTRY_KEYWORDS = ["intern", "junior", "associate", "entry level", "new grad", "graduate"]
SENIOR_KEYWORDS = ["senior", "sr.", "sr ", "staff", "lead", "principal", "director",
                   "head of", "vp,", "vp ", "chief", "executive"]


def infer_experience_level(title):
    title_lower = title.lower()
    for kw in SENIOR_KEYWORDS:
        if kw in title_lower:
            return "Senior/Leadership"
    for kw in ENTRY_KEYWORDS:
        if kw in title_lower:
            return "Entry-level"
    return "Mid-level"


# ---------- Step 2: work mode ----------

def first_location(location_name):
    """Multi-location jobs list locations separated by ';' - take the first."""
    return location_name.split(";")[0].strip()


def infer_work_mode(location_text, metadata):
    # Anthropic-style override: use Location Type metadata when present
    for m in (metadata or []):
        if m.get("name") == "Location Type" and m.get("value"):
            val = str(m["value"]).lower()
            if "remote" in val:
                return "Remote"
            if "hybrid" in val:
                return "Hybrid"
            if "on-site" in val or "onsite" in val:
                return "Onsite"

    # Fallback: infer from location text itself
    loc_lower = location_text.lower()
    if "remote" in loc_lower or "distributed" in loc_lower:
        return "Remote"
    if "hybrid" in loc_lower:
        return "Hybrid"
    return "Onsite"


# ---------- Step 3: geocoding ----------

# Strings that show up in the `location` field but are NOT real places -
# work-mode descriptors, placeholders, or garbage. NEVER geocode these -
# they'll match some unrelated real place by coincidence and produce a
# wrong-but-real-looking coordinate, which is worse than no coordinate.
NON_PLACE_LOCATIONS = {
    "hybrid", "distributed", "remote", "various", "multiple locations",
    "flexible", "worldwide", "n/a", "na", "tbd", "unknown", "",
}

# Static lookup for common cities - avoids network calls entirely for these.
# Extend this as you add more companies and see new recurring locations.
STATIC_CITY_COORDS = {
    "san francisco, ca": (37.7749, -122.4194),
    "new york city, ny": (40.7128, -74.0060),
    "new york, ny": (40.7128, -74.0060),
    "seattle, wa": (47.6062, -122.3321),
    "london, uk": (51.5074, -0.1278),
    "dublin, ie": (53.3498, -6.2603),
    "sydney, australia": (-33.8688, 151.2093),
    "tokyo, japan": (35.6762, 139.6503),
    "japan": (36.2048, 138.2529),
    "montreal, canada": (45.5019, -73.5674),
    "montréal": (45.5019, -73.5674),
    "mexico city, mexico": (19.4326, -99.1332),
    "são paulo, brazil": (-23.5505, -46.6333),
    "toronto, canada": (43.6532, -79.3832),
    "chicago, il": (41.8781, -87.6298),
    "austin, tx": (30.2672, -97.7431),
    "boston, ma": (42.3601, -71.0589),
    "los angeles, ca": (34.0522, -118.2437),
    "denver, co": (39.7392, -104.9903),
    "singapore": (1.3521, 103.8198),
    "bangalore, india": (12.9716, 77.5946),
    "bengaluru, india": (12.9716, 77.5946),
    "hyderabad, india": (17.3850, 78.4867),
    "amsterdam, netherlands": (52.3676, 4.9041),
    "paris, france": (48.8566, 2.3522),
    "berlin, germany": (52.5200, 13.4050),
}


def load_geocode_cache():
    if GEOCODE_CACHE_FILE.exists():
        return json.loads(GEOCODE_CACHE_FILE.read_text())
    return {}


def save_geocode_cache(cache):
    GEOCODE_CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def geocode_nominatim(location_text):
    """Call OpenStreetMap Nominatim - free, but rate-limited to 1 req/sec."""
    url = (
        "https://nominatim.openstreetmap.org/search?q="
        + location_text.replace(" ", "+")
        + "&format=json&limit=1"
    )
    req = Request(url, headers={"User-Agent": "jobxplo-mvp (personal project)"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except (URLError, ValueError, KeyError, IndexError):
        pass
    return None


def geocode(location_text, cache):
    """Always returns a (lat, lon) tuple - values may be None if unresolved."""
    key = location_text.lower().strip()

    if key in NON_PLACE_LOCATIONS:
        return None, None

    if key in STATIC_CITY_COORDS:
        return STATIC_CITY_COORDS[key]

    if key in cache:
        val = cache[key]
        return (val[0], val[1]) if val else (None, None)

    result = geocode_nominatim(location_text)
    cache[key] = list(result) if result else None
    time.sleep(1)  # respect Nominatim's 1 req/sec usage policy
    return result if result else (None, None)


# ---------- Step 4: freshness ----------

def compute_freshness(first_published_str):
    """Returns 'today' / 'yesterday' / '2 days ago' / None (drop)."""
    try:
        posted = datetime.fromisoformat(first_published_str)
    except (ValueError, TypeError):
        return None

    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    days_diff = (now.date() - posted.date()).days

    if days_diff == 0:
        return "today"
    elif days_diff == 1:
        return "yesterday"
    elif days_diff == 2:
        return "2 days ago"
    else:
        return None  # older than 2 days - drop entirely


# ---------- Main pipeline ----------

def main():
    cache = load_geocode_cache()
    all_jobs = []
    seen_urls = set()

    dropped_old = 0
    dropped_dupe = 0
    missing_geo = 0
    freshness_counts = {"today": 0, "yesterday": 0, "2 days ago": 0}
    exp_counts = {"Entry-level": 0, "Mid-level": 0, "Senior/Leadership": 0}
    mode_counts = {"Onsite": 0, "Remote": 0, "Hybrid": 0}

    for f in sorted(PROCESSED_DIR.glob("*.json")):
        jobs = json.load(open(f))["jobs"]

        for j in jobs:
            url = j.get("absolute_url")
            if not url:
                continue

            # Step 5: dedupe by job URL
            if url in seen_urls:
                dropped_dupe += 1
                continue

            # Step 4: freshness - drop if older than 2 days or unparseable
            freshness = compute_freshness(j.get("first_published"))
            if freshness is None:
                dropped_old += 1
                continue

            loc_text = first_location(j["location"]["name"])

            # Step 3: geocode - keep the job even if we can't place a pin
            lat, lon = geocode(loc_text, cache)
            if lat is None:
                missing_geo += 1

            exp_level = infer_experience_level(j["title"])
            work_mode = infer_work_mode(loc_text, j.get("metadata"))

            record = {
                "company": j["company_name"],
                "raw_title": j["title"],
                "role_category": j.get("role_category", "Other"),
                "experience_level": exp_level,
                "work_mode": work_mode,
                "location_text": loc_text,
                "lat": lat,
                "long": lon,
                "date_posted": j["first_published"][:10],
                "freshness": freshness,
                "job_url": url,
            }

            all_jobs.append(record)
            seen_urls.add(url)
            freshness_counts[freshness] += 1
            exp_counts[exp_level] += 1
            mode_counts[work_mode] += 1

    save_geocode_cache(cache)

    OUTPUT_FILE.write_text(json.dumps({"jobs": all_jobs}, indent=2, ensure_ascii=False))

    print("=" * 55)
    print(f"Total jobs written to data/jobs.json: {len(all_jobs)}")
    print(f"Dropped - older than 2 days:  {dropped_old}")
    print(f"Dropped - duplicate URL:      {dropped_dupe}")
    print(f"Missing geocode (kept, lat/long null): {missing_geo}")
    print()
    print("Freshness breakdown:", freshness_counts)
    print("Experience breakdown:", exp_counts)
    print("Work mode breakdown:", mode_counts)
    print("=" * 55)


if __name__ == "__main__":
    main()
