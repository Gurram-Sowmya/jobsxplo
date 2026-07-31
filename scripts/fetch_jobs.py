"""
Jobxplo — Stage 4: data fetcher.

Pulls raw job postings from each company's Greenhouse Job Board API
and saves the raw response to data/raw/{board_token}.json.

This step deliberately does NOT normalize/clean the data yet — that's
Stage 5/6. Keeping raw pulls separate from processed output makes it
easy to re-run processing later without re-fetching, and makes bugs
easier to debug (you can always check: was the raw pull wrong, or did
processing corrupt something?).

Usage:
    python scripts/fetch_jobs.py
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANIES_FILE = ROOT / "companies.json"
RAW_DIR = ROOT / "data" / "raw"

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
REQUEST_TIMEOUT_SECONDS = 15
DELAY_BETWEEN_REQUESTS_SECONDS = 1.5  # be a polite, rate-limited citizen


def fetch_greenhouse_board(board_token: str) -> dict | None:
    """Fetch raw job list for one Greenhouse board. Returns None on failure."""
    url = GREENHOUSE_BASE.format(token=board_token)
    request = urllib.request.Request(url, headers={"User-Agent": "jobxplo-fetcher/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                print(f"  [warn] {board_token}: unexpected status {response.status}")
                return None
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  [error] {board_token}: HTTP {e.code} — board token may be wrong or board is private")
        return None
    except urllib.error.URLError as e:
        print(f"  [error] {board_token}: network error — {e.reason}")
        return None
    except json.JSONDecodeError:
        print(f"  [error] {board_token}: response was not valid JSON")
        return None


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    companies = json.loads(COMPANIES_FILE.read_text())

    results = []
    for company in companies:
        if company["ats"] != "greenhouse":
            print(f"[skip] {company['name']}: ATS '{company['ats']}' not yet supported by this script")
            continue

        token = company["board_token"]
        print(f"[fetch] {company['name']} (board: {token})")
        data = fetch_greenhouse_board(token)

        if data is None or "jobs" not in data:
            print(f"  -> FAILED for {company['name']}, skipping")
            results.append({"company": company["name"], "status": "failed", "job_count": 0})
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)
            continue

        job_count = len(data["jobs"])
        out_path = RAW_DIR / f"{token}.json"
        out_path.write_text(json.dumps(data, indent=2))
        print(f"  -> OK, {job_count} jobs saved to {out_path.relative_to(ROOT)}")
        results.append({"company": company["name"], "status": "ok", "job_count": job_count})

        time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

    print("\n--- Summary ---")
    for r in results:
        print(f"  {r['company']:<15} {r['status']:<8} {r['job_count']} jobs")


if __name__ == "__main__":
    main()
