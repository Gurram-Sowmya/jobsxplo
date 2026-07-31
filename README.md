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
