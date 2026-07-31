# Jobxplo

Live, no-login, 3D globe of jobs posted today/yesterday/2-days-ago — pulled directly from company ATS feeds.

## Stage 3 status
This is the environment-setup skeleton. It contains:
- `index.html` — placeholder page (will become the 3D globe in Stage 8)
- `data/jobs.json` — placeholder dataset (will hold real job data from Stage 6 onward)
- `.github/workflows/update-data.yml` — scheduled automation skeleton (real fetch/process logic replaces the placeholder step in Stage 4-7)

## Setup steps (do these once)
1. Create a new **public** GitHub repo named `jobxplo`.
2. Push everything in this folder to that repo (see commands below).
3. Go to your repo's **Settings → Actions → General** and confirm "Read and write permissions" is enabled for the `GITHUB_TOKEN` (needed for the workflow to commit data back).
4. Go to the **Actions** tab, select "Update job data", and click **Run workflow** to trigger it manually — confirm it runs green and `data/jobs.json`'s `generated_at` field updates.
5. Sign up for **Cloudflare Pages** (or Vercel/Netlify), connect it to this GitHub repo, and deploy. Any of these auto-redeploy on every push.
6. Confirm the deployed URL loads the placeholder page.

## Push commands (run in this folder)
```
git init
git add .
git commit -m "Stage 3: environment setup skeleton"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/jobxplo.git
git push -u origin main
```

## Exit criteria for Stage 3
- [ ] Repo exists on GitHub with this skeleton pushed
- [ ] The GitHub Actions workflow runs successfully (manually triggered first, then confirm it fires on the 6-hour schedule too)
- [ ] The placeholder site is live at a public Cloudflare Pages/Vercel/Netlify URL
- [ ] A push to `main` triggers an automatic redeploy

Once all four are checked, Stage 3 is done — move to Stage 4 (real data fetcher).

## Stage 4: real data fetcher

`scripts/fetch_jobs.py` pulls raw job data from each company listed in `companies.json`
(currently all on Greenhouse) and saves it to `data/raw/{board_token}.json`.

**Run it locally first, before wiring it into GitHub Actions**, so you can see errors directly:
```
python scripts/fetch_jobs.py
```

**Important**: only Stripe's board token (`stripe`) has been live-verified. The rest in
`companies.json` use the standard "lowercase company name" convention Greenhouse boards
usually follow, but that's an assumption, not a confirmed fact — the script will print
`[error]` for any token that's wrong. Check each failure by visiting
`https://boards.greenhouse.io/{token}` in a browser to find the real token, then update
`companies.json`.

**Note on dates**: use each job's `first_published` field for freshness tagging in Stage 5/6,
not `updated_at` — Greenhouse's `updated_at` reflects the last bulk resync of the whole board,
so it's identical across most jobs and does not mean the listing is actually new.

### Exit criteria for Stage 4
- [ ] Running the script locally produces at least one real `data/raw/*.json` file with jobs in it
- [ ] Every company in `companies.json` either succeeds or you've corrected its board token
- [ ] You've spot-checked one job entry and confirmed `first_published`, `title`, `location.name`, and `absolute_url` all look correct

## Stage 5: role taxonomy mapping

`data/role_taxonomy.json` holds the fixed list of ~38 canonical role categories (Software
Engineer, Data Engineer, Product Manager, etc.) — this is the dropdown list the user will
eventually filter by.

`scripts/map_roles.py` reads every file in `data/raw/` (from Stage 4), and for each job:
1. Tries **keyword rules** first (e.g. any title containing "data engineer" maps straight to
   Data Engineer). Handles most titles for free.
2. Falls back to **fuzzy text matching** (Python's built-in `difflib`, no install needed) for
   titles that don't match any keyword.
3. Saves the result to `data/processed/{company}.json`, with the original `raw_title` kept
   untouched and a new `role_category` field added.

Run it locally:
```
python scripts/map_roles.py
```

It prints a summary: how many jobs were mapped by keyword vs. fuzzy fallback, and how many
fell through to "Other" (the catch-all bucket). A high "Other" rate means the keyword rules
need tuning — check `data/processed/*.json` for a few real (raw_title -> role_category) pairs
that look wrong and feed them back in to improve the rules.

### Exit criteria for Stage 5
- [ ] Running the script produces `data/processed/*.json` files with a `role_category` on every job
- [ ] You've spot-checked 10-15 real jobs and their assigned category makes sense
- [ ] "Other" rate is reasonably low (a handful is fine — 0% is not the bar)
