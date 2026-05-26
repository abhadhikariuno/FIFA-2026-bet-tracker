-- FIFA 2026 Bet Tracker — Supabase Schema
-- Run this in your Supabase project → SQL Editor

-- ── TABLES ──────────────────────────────────────────────────────

create table public.users (
  id text primary key,          -- Google OAuth sub (unique per Google account)
  email text unique not null,
  name text,
  avatar_url text,
  created_at timestamptz default now()
);

create table public.allowlist (
  email text primary key,
  name text,
  added_at timestamptz default now()
);

create table public.matches (
  id serial primary key,
  match_number int unique,
  stage text not null,           -- 'Group','R32','R16','QF','SF','3rd','Final'
  group_name text,               -- 'A'-'L' for group stage, null for knockouts
  team1 text not null,
  team2 text not null,
  match_date date,
  match_time text,               -- local kick-off e.g. '8:00 PM ET'
  venue text,
  city text,
  created_at timestamptz default now()
);

create table public.picks (
  id uuid primary key default gen_random_uuid(),
  user_id text references public.users(id) on delete cascade,
  match_id int references public.matches(id) on delete cascade,
  team_pick text not null,
  created_at timestamptz default now(),
  unique(user_id, match_id)
);

create table public.results (
  match_id int primary key references public.matches(id) on delete cascade,
  winner text not null,          -- team name or 'NR' (no result)
  stake decimal not null default 10,
  posted_at timestamptz default now()
);

-- ── ROW LEVEL SECURITY ───────────────────────────────────────────
-- Auth is handled client-side via Google JWT; these policies allow
-- the anon key full access (acceptable for a private friend-group app).

alter table public.users     enable row level security;
alter table public.allowlist enable row level security;
alter table public.matches   enable row level security;
alter table public.picks     enable row level security;
alter table public.results   enable row level security;

create policy "open" on public.users     for all using (true) with check (true);
create policy "open" on public.allowlist for all using (true) with check (true);
create policy "open" on public.matches   for all using (true) with check (true);
create policy "open" on public.picks     for all using (true) with check (true);
create policy "open" on public.results   for all using (true) with check (true);

-- ── SEED: ALLOWLIST ──────────────────────────────────────────────
-- Add player emails here before sharing the app link.
-- insert into public.allowlist(email, name) values
--   ('you@gmail.com', 'Your Name'),
--   ('friend@gmail.com', 'Friend Name');

-- ── SEED: GROUP STAGE MATCHES ────────────────────────────────────
-- FIFA 2026 group draw (Dec 5 2024). Dates/times TBC — update as schedule is confirmed.
-- Host cities: 11 USA + 2 Canada + 3 Mexico venues.
-- Run the inserts below AFTER confirming dates with the official schedule.

-- Example format (fill in real dates/venues):
-- insert into public.matches(match_number,stage,group_name,team1,team2,match_date,match_time,city) values
--   (1,'Group','A','Mexico','TBD','2026-06-11','5:00 PM ET','Mexico City'),
--   ...;
