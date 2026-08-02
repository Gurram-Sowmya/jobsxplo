# Jobxplo

Live, no-login, 3D globe of jobs posted today/yesterday/2-days-ago — pulled directly from company ATS feeds.

## Current status: Stage 12 nearly complete (one confirmation pending)

There's a real, live, self-updating site: a 3D globe (`index.html`, built with `globe.gl`) that loads `data/jobs.json` — which regenerates itself automatically every 6 hours (Stage 7) from **14 companies** — and plots one dot per job, colored by freshness. Five filters (Role, Work mode, Experience, Location, Company) narrow the globe instantly in the browser, plus a clickable freshness legend and a rotation pause/resume button. The site is responsive on both desktop and mobile. Confirmed live: the Company dropdown correctly shows ~10 of the 14 companies at any given time - the other ~4 simply don't have a posting inside the current 2-day freshness window, which is expected, correct behavior, not a bug.

**Bonus feature added during Stage 9 polish:** a "Show borders" button overlays free Natural Earth country/state boundary data on the globe. Confirmed working live.

**Stage 5 bug fix (post Stage 6 review):** an earlier version of `scripts/map_roles.py` had ~145 categories' worth of keyword rules accidentally left inert inside a text block instead of running as real code, which pushed ~23% of jobs into an unhelpful "Other" catch-all. Those rules were recovered, merged onto the existing 41-category taxonomy (no new categories added, to keep the filter list clean), and verified — "Other" rate dropped to ~17%. This is why `scripts/map_roles.py` may look denser than a first draft would.

Repo contents:
- `companies.json` — 14 companies, all on Greenhouse, live and confirmed
- `scripts/fetch_jobs.py` — Stage 4: pulls raw job data per company
- `scripts/map_roles.py` — Stage 5: maps messy raw titles to a fixed role taxonomy
- `scripts/process_jobs.py` — Stage 6: adds experience level, work mode, coordinates, freshness; produces the final dataset
- `data/role_taxonomy.json` — the 41 fixed role categories used for the Role filter
- `data/raw/*.json` — one file per company, raw ATS data (Stage 4 output)
- `data/processed/*.json` — one file per company, with `role_category` added (Stage 5 output)
- `data/geocode_cache.json` — cached lat/long lookups, so re-running never re-hits the geocoding service for a location it's already resolved
- `data/jobs.json` — the final, live dataset the frontend will read (Stage 6 output) — **regenerated automatically every 6 hours (Stage 7)**
- `index.html` — **the real 3D globe (Stage 8), with filters, freshness controls, mobile-responsive layout (Stage 9), and a border overlay**
- `.github/workflows/update-data.yml` — the real scheduled pipeline (Stage 7) — runs fetch → map → process → commit automatically
- `vercel.json` — sets caching headers on `data/jobs.json` so devices always check for fresh data (Stage 12)

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

## Stage 7: pipeline automation

**What it is:** `.github/workflows/update-data.yml` now runs the real pipeline instead of the Stage 3 placeholder timestamp step. On a schedule (every 6 hours) and on-demand (via the **Run workflow** button on the Actions tab), it runs, in order:

1. Check out the repo
2. Set up Python
3. `python3 scripts/fetch_jobs.py` (Stage 4 — pulls fresh raw data)
4. `python3 scripts/map_roles.py` (Stage 5 — assigns role categories)
5. `python3 scripts/process_jobs.py` (Stage 6 — geocodes, tags freshness, dedupes, writes `data/jobs.json`)
6. Commits and pushes `data/` back to the repo, only if something actually changed

**Why this matters:** this is the step that turns Jobxplo from "a script I have to remember to run" into "a site that keeps itself current on its own." From this point on, `data/jobs.json` reflects real postings from the last 2 days without anyone touching it — including while asleep, on a different device, or after the project is handed off to someone else entirely.

**A couple of things worth knowing:**
- The commit step only pushes when there's an actual change (`git diff --quiet ... || git commit`), so the repo's history doesn't fill up with empty "nothing changed" commits.
- A "Node.js 20 is deprecated" warning may show up in the Actions log — this is GitHub's own infrastructure notice about the runner environment, not an error in this project's code, and needs no action.

### Exit criteria
- [x] Workflow file updated to run the real 3-script pipeline instead of the placeholder
- [x] Manually triggered run completes with a green checkmark on all steps (Fetch, Map, Process, Commit)
- [x] `data/jobs.json` in the repo shows real job entries after the run, not the empty placeholder
- [ ] Confirmed a scheduled (non-manual) run fires on its own after 6 hours, without anyone clicking anything

---

## Stage 8: globe frontend

**What it is:** `index.html` replaced the Stage 3 placeholder with a real 3D Earth, built using `globe.gl` (loaded from a public CDN, no install/build step needed — it's a single static HTML file). On load, it fetches `data/jobs.json` and plots one point per job that has a resolved `lat`/`long`, colored by `freshness`. Hovering a point shows the company, title, location, and work mode; clicking it opens `job_url` in a new tab.

**Design decisions worth knowing:**
- Jobs with `lat: null` (unresolved locations — see Stage 6) are intentionally **not plotted**, rather than guessed at a default position. The status readout in the corner reports how many were skipped this way, so that number is always visible, not hidden.
- Rotation is drag-to-orbit by default (built into `globe.gl`), plus a gentle **auto-rotate** so it's obviously interactive even without touching it — dragging temporarily overrides the auto-spin, then it resumes.
- The whole page is one dependency-free HTML file — no build tools, no `npm install` — so it can be edited and re-uploaded directly through GitHub's web editor, which matters a lot for a no-local-dev-environment workflow.

### Exit criteria
- [x] Real dots (not placeholder content) render on a rotatable, zoomable 3D globe
- [x] Data comes from the live `data/jobs.json`, not hardcoded sample data
- [x] Clicking a dot opens the real, original job posting

---

## Stage 9: filter UI

**What it is:** five dropdowns (Role, Work mode, Experience, Location, Company) plus a clickable freshness legend (Today / Yesterday / 2 days ago) and a rotation pause/resume button, all added directly into `index.html`. Every filter runs **entirely in the browser** — picking a filter re-reads the already-downloaded `data/jobs.json` in memory and redraws the globe; nothing is re-fetched from the server.

**How the filter options are built:** Role, Location, and Company dropdowns populate themselves from whatever values actually exist in the current `data/jobs.json` — not a hardcoded list. This means a role/location/company only ever appears as a filter option when there's a real, currently-fresh job behind it; there's no such thing as picking a filter and getting zero results. It also means the dropdown contents change automatically as the dataset changes (e.g. as Stage 10 adds more companies), with no code changes needed.

**Location text cleanup:** raw location strings from company ATS feeds sometimes bundle the work mode into the place itself (e.g. `"Remote - India"`, `"Hybrid - London, UK"`). Since work mode already has its own filter, `index.html` strips those mode words out client-side before showing locations in the dropdown — so the Location filter shows `"India"` and `"London, UK"`, and Remote/Hybrid stay filterable through the Work mode dropdown instead. (Note: this cleanup happens in the frontend only; `data/jobs.json` itself still stores the original, unmodified `location_text` — worth eventually moving this same cleanup into Stage 6's `process_jobs.py` so the cleaned value is available anywhere the data is used, not just this one page.)

**Clickable freshness legend:** clicking "Today," "Yesterday," or "2 days ago" isolates that color on the globe; clicking the same one again (or "Clear filters") returns to showing all three.

### Exit criteria
- [x] All 5 filters correctly narrow the visible dots, individually and in combination
- [x] Filter dropdown options are driven by real data, not hardcoded
- [x] Freshness legend is clickable and toggles correctly
- [x] Rotation can be paused and resumed on demand
- [x] Layout is responsive - filters collapse behind a toggle on mobile so the globe stays the focus

**Bonus, built during Stage 9 polish (not originally scoped, added on request):** a "Show borders" toggle overlays real country and state/province outlines (free, public-domain Natural Earth data) directly on the globe, lazy-loaded on first click and cached after that. District-level boundaries were intentionally scoped out - no reliable free global dataset exists at that detail level; the existing job dots already serve as city-level markers. This part is built and syntax-verified, but not yet confirmed working live - worth a quick check next time you're in the app.

---

## Stage 10: multi-company integration

**What it is:** expanding `companies.json` from the original 7 companies to 14 (added Duolingo, Instacart, Discord, Robinhood, Dropbox, Reddit, Notion - all confirmed to run on Greenhouse). The pipeline itself needed no code changes for this; it was built in Stage 4-7 to handle any number of companies already. This was purely a data/config change.

### Exit criteria
- [x] Updated `companies.json` uploaded to the repo
- [x] Workflow manually re-run and completed successfully with the expanded list
- [x] Live site's Company filter dropdown confirmed to show the new companies (10 of 14 visible - expected, since the other 4 simply have no posting inside the current 2-day window)
- [ ] Deep spot-check that new companies didn't introduce any bad role mappings or broken locations *(optional - folded into Stage 11 below)*

**Status:** confirmed live and working.

---

## Stage 11: testing

**What it is:** a verification pass across the now-larger, 14-company dataset. Split into two parts:

1. **Manual, live-site checks (done):** each filter individually, filters combined, several dots clicked to confirm they open the correct real posting, freshness legend isolating the correct colors, mobile layout, and the border overlay - all confirmed working directly on the live site.
2. **Deep data-quality check (optional, not yet done):** the kind of review that caught the Stage 5 role-mapping bug - re-verifying date parsing, dedup, geocoding accuracy, and "Other" rate specifically against the 7 newly-added companies' data, in case any of them has an unusual title/date/location format the original 7 didn't. This requires the repo's `data/` and `scripts/` folders to be shared for review; it's optional extra confidence, not a blocker.

### Exit criteria
- [x] All filters verified individually and in combination on live data
- [x] Multiple dots spot-checked to confirm correct click-through
- [x] Freshness legend verified to isolate correct colors
- [x] Mobile layout re-confirmed
- [x] Border overlay confirmed working live
- [ ] Deep data-quality review of the 7 newly-added companies *(optional)*

**Status:** manually verified and passing. Considered complete for practical purposes; the optional deep check can be done anytime without blocking further progress.

---

## Stage 12: deployment

**What it is:** normally this stage means "get the tested app live for the first time" - but since this project has been live on Vercel since Stage 3 (every stage since has been tested on the real deployed site, not a local copy), most of this stage's work already happened along the way. What's left is closing the remaining gaps between "live" and "properly finished deployment":

**Caching investigation (resolved):** the site appeared to show stale job counts after a pipeline run. Traced step by step: (1) confirmed via GitHub's commit history that the pipeline genuinely had committed new data, (2) confirmed via Vercel's deployment list that the new commit was deployed to Production successfully. Both halves of the pipeline were working correctly - the stale view was the browser's own local cache, not a server or pipeline issue. `vercel.json` was added to explicitly set `Cache-Control: public, max-age=0, must-revalidate` on `data/jobs.json`, so browsers always check for fresh data instead of trusting a cached copy - this prevents the same confusion from happening again.

### Exit criteria
- [x] Publicly reachable by anyone, at all times (true since Stage 3)
- [x] Auto-redeploys on every commit (Vercel + GitHub integration, working since Stage 8)
- [x] Root-caused a data-freshness display issue - confirmed pipeline and deployment both working correctly; added explicit caching headers to prevent recurrence
- [ ] Hard-refresh confirmation that the live site now shows current data (pending)
- [x] Custom domain decision made - staying with the free `jobsxplo.vercel.app` link

**Status:** effectively done pending one confirmation - a hard refresh on the live site to confirm the current job count matches the latest pipeline run.

---

## Next: Stage 13 (soft launch)

Once Stage 12's two remaining boxes are checked, Stage 13 is about sharing the link with a small group first (rather than a big launch push) and watching for real-world edge cases in actual usage before Stage 14's ongoing iteration loop begins.