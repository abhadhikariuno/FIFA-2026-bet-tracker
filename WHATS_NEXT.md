# FIFA 2026 Bet Tracker — Current Status & What's Left

_Last updated: June 3, 2026 — 8 days to launch_

## What's Done

- [x] Google OAuth wired up (`GOOGLE_CLIENT_ID` filled in)
- [x] Supabase project created and connected (`SUPABASE_URL` + `SUPABASE_ANON_KEY` filled in)
- [x] Database schema deployed (5 tables: users, allowlist, matches, picks, results)
- [x] `fd_id` column added to matches (links to football-data.org)
- [x] `home_goals` / `away_goals` columns added to results (auto-populated by poller)
- [x] All 104 FIFA 2026 matches seeded via `scripts/seed_matches.py`
- [x] Admin email configured
- [x] Matches display grouped by match day with ← Prev / Next → navigation
- [x] Within each day, matches grouped by group (Group A, Group B, etc.)
- [x] Plain team names — no flag emojis or abbreviations
- [x] All times in CST
- [x] Draw betting supported for group stage (3-way: Team 1 | 🤝 Draw | Team 2)
- [x] Draw payouts work correctly for any split (1v3, 2v2, etc.)
- [x] Group standings show GD column, sorted by Pts → GD → GF
- [x] `scripts/poll_results.py` auto-fetches results + scores from football-data.org
- [x] When a group completes, bracket auto-refreshes (TBD slots fill in for R32)
- [x] GitHub repo created (private): `github.com/abhadhikariuno/FIFA-2026-bet-tracker`
- [x] GitHub Actions workflow polls results every 5 minutes automatically — no manual poller needed

---

## What's Left Before Launch

### 1. Add Friends to Allowlist

Run in Supabase SQL Editor:

```sql
INSERT INTO public.allowlist (email, name) VALUES
  ('friend1@gmail.com', 'Name'),
  ('friend2@gmail.com', 'Name');
```

Or use the **Settings** tab in the app once signed in as admin.

Also add them as **test users** in Google Cloud Console → APIs & Services → OAuth consent screen → Test users. Otherwise they'll get a "not authorized by Google" error.

### 2. Deploy

The app is a single `index.html`. The committed version has **empty credential placeholders** — your local file has real keys filled in but is intentionally not committed.

> ⚠️ The repo is **public**. Never run `git add index.html` — it will expose your Supabase anon key and Google Client ID in git history permanently.

**Option A — Netlify drag-and-drop (safest, no git exposure):**
1. netlify.com → Add new site → Deploy manually
2. Drag and drop your local `fifa-bet-tracker/` folder (with credentials filled in)
3. Copy the `*.netlify.app` URL

**Option B — GitHub Pages via Actions (credentials stay in GitHub Secrets):**
1. Add `GOOGLE_CLIENT_ID`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` to repo Settings → Secrets → Actions
2. Add a deploy workflow that uses `sed` to inject secrets into `index.html` before publishing to `gh-pages` branch
3. The `main` branch stays clean with empty placeholders

### 3. Add Production URL to Google OAuth

After deploying, go to Google Cloud Console → APIs & Services → Credentials → your OAuth client → add the live URL under **Authorized JavaScript origins**.

### 4. Run Payments Migration in Supabase

The payout ledger and Zelle features require two additions. Run this once in Supabase SQL Editor:

```sql
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS zelle_id text;

CREATE TABLE IF NOT EXISTS public.payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payer_id text NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  payee_id text NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  stage text NOT NULL,
  amount decimal(10,2) NOT NULL DEFAULT 0,
  confirmed boolean NOT NULL DEFAULT true,
  confirmed_at timestamptz,
  confirmed_by text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(payer_id, payee_id, stage)
);
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "open" ON public.payments FOR ALL USING (true) WITH CHECK (true);
```

After running, each player can add their Zelle ID under **More → Zelle**.

### 5. Add GitHub Actions Secrets

The poller runs automatically via `.github/workflows/` every 5 minutes on match days. Make sure these secrets are set in GitHub repo Settings → Secrets → Actions:

| Secret name | Where to get it |
|-------------|-----------------|
| `FD_API_KEY` | football-data.org dashboard |
| `SUPABASE_URL` | Supabase project settings |
| `SUPABASE_KEY` | Supabase project settings → anon key |

---

## Quick Reference

| Item | Value |
|------|-------|
| GitHub repo | `github.com/abhadhikariuno/FIFA-2026-bet-tracker` (private) |
| Supabase project | _(see Supabase dashboard)_ |
| Admin email | _(see ADMIN_EMAILS in index.html)_ |
| Group stage starts | June 11, 2026 |
| Total matches | 104 |

## Stake Reference

| Stage | Stake |
|-------|-------|
| Group | $10 |
| Round of 32 | $15 |
| Round of 16 | $20 |
| Quarter-finals | $30 |
| Semi-finals | $50 |
| 3rd Place | $30 |
| Final | $100 |

## Payout Model

Losers' stakes go into a pot, winners split it equally.

Example — 4 players, Group stage ($10 stake):
- 2 pick Brazil, 1 picks Argentina, 1 picks Draw → Draw happens
- 1 Draw picker wins $30 (collects from 3 losers) — but wait, 1 winner here
- 2 pick Draw → each wins $10 (split $20 pot from 2 losers)

## Optional Enhancements

- **Real-time sync** — add Supabase channel subscription so picks/results update live without manual refresh:
  ```javascript
  supabase.channel('results')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'results' }, () => loadAll())
    .subscribe();
  ```
- **Stricter RLS** — add proper Supabase row-level security policies tied to Google JWT if you want to lock down the database beyond the allowlist check
