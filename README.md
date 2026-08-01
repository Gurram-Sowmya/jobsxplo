# Jobxplo

Live, no-login, 3D globe of jobs posted today/yesterday/2-days-ago — pulled directly from company ATS feeds.

## Current status: Stage 6 complete

The pipeline now runs end to end locally: fetch → map roles → process (experience level, work mode, geocoding, freshness, dedupe) → final `data/jobs.json`. What's still missing: automation (Stage 7) and the actual 3D globe frontend (Stage 8) — right now `index.html` is still the Stage 3 placeholder page.

Repo contents:
- `companies.json` — list of companies to fetch, with their Greenhouse board tokens
- `scripts/fetch_jobs.py` — Stage 4: pulls raw job data per company
- `scripts/map_roles.py` — Stage 5: maps messy raw titles to a fixed role taxonomy
- `scripts/process_jobs.py` — Stage 6: adds experience level, work mode, coordinates, freshness; produces the final dataset
- `data/role_taxonomy.json` — the 41 fixed role categories used for the Role filter
- `data/raw/*.json` — one file per company, raw ATS data (Stage 4 output)
- `data/processed/*.json` — one file per company, with `role_category` added (Stage 5 output)
- `data/geocode_cache.json` — cached lat/long lookups, so re-running never re-hits the geocoding service for a location it's already resolved
- `data/jobs.json` — the final, live dataset the frontend will read (Stage 6 output)
- `index.html` — still the Stage 3 placeholder; becomes the real globe in Stage 8
- `.github/workflows/update-data.yml` — automation skeleton; becomes the real scheduled pipeline in Stage 7

---

## Stage 3: environment setup

**What it is:** the empty skeleton — repo, hosting, and a workflow file that don't do anything real yet, just prove the plumbing works.

### Setup steps (do these once)
1. Create a new public GitHub repo named `jobxplo`.
2. Push everything in this folder to that repo:
   ```
   git init
   git add .
   git commit -m "Stage 3: environment setup skeleton"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/jobxplo.git
   git push -u origin main
   ```
3. In the repo, go to **Settings → Actions → General** and confirm "Read and write permissions" is enabled for `GITHUB_TOKEN` (the scheduled workflow will need this later to commit updated data back to the repo).
4. Go to the **Actions** tab, select "Update job data", and click **Run workflow** to trigger it manually — confirm it runs green.
5. Sign up for Cloudflare Pages (or Vercel/Netlify), connect it to this GitHub repo, and deploy. Any of these auto-redeploy on every push to `main`.
6. Confirm the deployed URL loads the placeholder page.

### Exit criteria
- [ ] Repo exists on GitHub with the skeleton pushed
- [ ] The GitHub Actions workflow runs successfully when triggered manually
- [ ] The placeholder site is live at a public URL
- [ ] A push to `main` triggers an automatic redeploy

---

## Stage 4: real data fetcher

**What it is:** `scripts/fetch_jobs.py` pulls raw job data from each company listed in `companies.json` (all on Greenhouse currently) and saves it to `data/raw/{board_token}.json`.

Run it locally first, before wiring it into GitHub Actions, so you can see errors directly:
```
python3 scripts/fetch_jobs.py
```

**Important — only some board tokens are pre-verified.** `companies.json` uses the standard "lowercase company name" convention Greenhouse boards usually follow, but that's an assumption per-company, not a confirmed fact. The script prints `[error]` for any token that's wrong. To fix a failing one, visit `https://boards.greenhouse.io/{token}` in a browser to find the real token, then update `companies.json`.

**Critical — which date field means what.** Every raw job record has both `first_published` and `updated_at`. Use **`first_published`** for freshness tagging (Stage 6) — never `updated_at`. Greenhouse's `updated_at` reflects the last bulk resync of the whole board, so it's nearly identical across most jobs regardless of when the job actually went live. Using it would make almost every job on the board look "posted today," which defeats the entire point of the app.

### Exit criteria
- [ ] Running the script locally produces at least one real `data/raw/*.json` file with jobs in it
- [ ] Every company in `companies.json` either succeeds or you've corrected its board token
- [ ] Spot-checked one job entry and confirmed `first_published`, `title`, `location.name`, and `absolute_url` all look correct

---

## Stage 5: role taxonomy & mapping

**What it is:** `data/role_taxonomy.json` holds the fixed list of 41 canonical role categories (Software Engineer, Data Engineer, Product Manager, etc.) — this is the exact dropdown list the user will filter by on the live site. `scripts/map_roles.py` reads every file in `data/raw/` and, for each job, assigns one of those 41 categories to a new `role_category` field.

Two-step mapping, cheapest first:
1. **Keyword rules** — if the title contains an obvious keyword (e.g. "data engineer"), map it directly. Free, fast, handles most titles.
2. **Fuzzy fallback** — for titles that don't match any keyword rule, use `difflib` (built into Python, no install needed) to find the closest canonical category by text similarity. If nothing is close enough, the job falls to `"Other"` — an honest "we're not sure" rather than a wrong guess.

Run it locally:
```
python3 scripts/map_roles.py
```

It prints a summary — how many jobs mapped by keyword vs. fuzzy fallback, and how many fell through to `"Other"`. It also runs an automatic self-check on startup: if any keyword rule points at a category name that isn't actually in `role_taxonomy.json`, the script refuses to run and prints exactly which ones are wrong. **Don't skip this check if it fires** — a `role_category` that isn't a real filter option means that job becomes permanently invisible to anyone using the Role filter, even though it's sitting right there in the data.

**A low "Other" rate isn't automatically good.** It can also mean the fuzzy matcher is confidently guessing wrong instead of admitting it doesn't know. Always spot-check actual `(raw_title -> role_category)` pairs from `data/processed/*.json`, not just the summary numbers — a bad fuzzy match (e.g. a "Solutions Architect" title landing on "Executive Assistant") is worse than an honest "Other," because it silently misfiles a real job under a filter where users will never think to look for it.

### Exit criteria
- [ ] Running the script produces `data/processed/*.json` with `role_category` on every job
- [ ] Spot-checked 10–15 real jobs and their assigned category makes sense
- [ ] "Other" rate is reasonably low — a meaningful chunk is fine (0% is not the bar; some titles are genuinely ambiguous or non-English, and those should honestly land in Other, not be forced into a wrong category)

---

## Stage 6: data processing layer

**What it is:** `scripts/process_jobs.py` reads `data/processed/*.json` (Stage 5 output) and adds the remaining fields needed to match the final schema, then writes the single, final `data/jobs.json` that the frontend will read.

Run it locally:
```
python3 scripts/process_jobs.py
```

What it does, step by step:

1. **Experience level** — inferred from title keywords. Checks for Senior/Staff/Lead/Principal/Director-type keywords *before* checking for Entry-level keywords, so a title like "Senior Associate" correctly lands as Senior/Leadership rather than Entry-level.
2. **Work mode** — inferred primarily from the location text itself (e.g. a location string containing "remote" or "distributed" → Remote), since most companies don't expose a reliable structured remote/onsite field. Where a company's ATS *does* provide one (Anthropic's `Location Type` metadata, when populated), that's used as an override.
3. **Geocoding** — converts `location_text` into lat/long for plotting on the globe. Checks a small static city lookup table first (free, instant), then falls back to OpenStreetMap Nominatim for anything not in the table, respecting its 1-request/second usage policy. Every result is cached in `data/geocode_cache.json` so re-runs never repeat a network call for a location already resolved.
   - **Non-place strings are blocked from geocoding entirely.** Some companies put work-mode descriptors like `"Hybrid"`, `"Distributed"`, or placeholder values like `"N/A"` directly in the location field instead of a real place. Sending these to Nominatim returns a real-but-meaningless coordinate (e.g. a rural town picked by coincidental text similarity) — worse than no coordinate at all, since it silently plots a job in the wrong place on the globe. These are caught and correctly left as `lat: null, long: null` instead.
   - Jobs with no resolvable coordinate are **kept** in the dataset (still filterable by role/company/experience/work mode), just not plotted as a globe marker.
4. **Freshness** — computed from `first_published` (see the Stage 4 note above on why not `updated_at`). Tags each job `today` / `yesterday` / `2 days ago`. Anything older is **dropped from the output entirely** — never sent to the frontend at all, per the core product rule.
5. **Dedupe** — by `absolute_url`, the unique identifier for each posting.

If you delete `data/geocode_cache.json` and re-run, the pipeline still works correctly (it just re-resolves everything from scratch, a bit slower). Do this deliberately after any change to the geocoding blocklist or lookup table, since a stale cache entry can otherwise mask a fix.

### Exit criteria
- [ ] Running the script produces `data/jobs.json` matching the full schema (company, raw_title, role_category, experience_level, work_mode, location_text, lat, long, date_posted, freshness, job_url)
- [ ] Spot-checked several real entries — freshness, work mode, and coordinates all look correct
- [ ] No non-place location strings ("Hybrid", "N/A", etc.) produced a fake coordinate
- [ ] Postings older than 2 days are confirmed absent from the output, not just marked

---

## Next: Stage 7 (pipeline automation)

Wrap `fetch_jobs.py` → `map_roles.py` → `process_jobs.py` into the scheduled GitHub Actions workflow (`.github/workflows/update-data.yml`), so `data/jobs.json` regenerates itself every few hours without anyone running it by hand.