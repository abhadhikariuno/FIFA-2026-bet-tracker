"""
seed_matches.py — Pull FIFA 2026 full schedule from football-data.org
                  and insert all matches into Supabase.

Setup:
    pip install requests pytz
    python seed_matches.py

Run ONCE before the tournament starts.
"""

import os, sys, time, requests
from datetime import datetime
import pytz

# ── CONFIG ───────────────────────────────────────────────────
import os
FD_API_KEY   = os.environ['FD_API_KEY']
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
FD_BASE      = 'https://api.football-data.org/v4'
ET           = pytz.timezone('America/Chicago')
# ─────────────────────────────────────────────────────────────

STAGE_MAP = {
    'GROUP_STAGE':    'Group',
    'LAST_32':        'R32',
    'LAST_16':        'R16',
    'QUARTER_FINALS': 'QF',
    'SEMI_FINALS':    'SF',
    'THIRD_PLACE':    '3rd',
    'FINAL':          'Final',
}

VENUE_CITY = {
    'Estadio Azteca':             'Mexico City',
    'Estadio Akron':              'Guadalajara',
    'Estadio BBVA':               'Monterrey',
    'BC Place':                   'Vancouver',
    'BMO Field':                  'Toronto',
    'MetLife Stadium':            'New York/New Jersey',
    'Gillette Stadium':           'Boston',
    'Lincoln Financial Field':    'Philadelphia',
    'AT&T Stadium':               'Dallas',
    'NRG Stadium':                'Houston',
    'Arrowhead Stadium':          'Kansas City',
    'SoFi Stadium':               'Los Angeles',
    "Levi's Stadium":             'San Francisco Bay Area',
    'Allegiant Stadium':          'Las Vegas',
    'Hard Rock Stadium':          'Miami',
    'Mercedes-Benz Stadium':      'Atlanta',
    'Empower Field at Mile High': 'Denver',
    'Lumen Field':                'Seattle',
}


def fd_get(path):
    r = requests.get(f'{FD_BASE}{path}', headers={'X-Auth-Token': FD_API_KEY})
    # honour rate-limit header if present
    if r.status_code == 429:
        wait = int(r.headers.get('X-RequestCounter-Reset', 60))
        print(f'  Rate limited — waiting {wait}s …')
        time.sleep(wait)
        return fd_get(path)
    r.raise_for_status()
    return r.json()


def sb_headers():
    return {
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type':  'application/json',
    }


def sb_upsert(table, rows):
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/{table}',
        headers={**sb_headers(), 'Prefer': 'resolution=merge-duplicates,return=minimal'},
        params={'on_conflict': 'match_number'},
        json=rows,
    )
    if r.status_code not in (200, 201):
        print(f'  Supabase error {r.status_code}: {r.text[:300]}')
    return r.ok


def main():
    print('Fetching FIFA 2026 schedule from football-data.org …')
    data = fd_get('/competitions/WC/matches')
    raw  = data.get('matches', [])
    print(f'  {len(raw)} matches returned.')

    rows = []
    for i, m in enumerate(raw, 1):
        utc_dt = datetime.fromisoformat(m['utcDate'].replace('Z', '+00:00'))
        et_dt  = utc_dt.astimezone(ET)

        group_raw = (m.get('group') or '').replace('GROUP_', '') or None
        venue     = m.get('venue') or ''
        city      = VENUE_CITY.get(venue, '')
        stage     = STAGE_MAP.get(m['stage'], m['stage'])

        rows.append({
            'match_number': i,
            'fd_id':        m['id'],
            'stage':        stage,
            'group_name':   group_raw,
            'team1':        m['homeTeam'].get('name') or 'TBD',
            'team2':        m['awayTeam'].get('name') or 'TBD',
            'match_date':   et_dt.strftime('%Y-%m-%d'),
            'match_time':   et_dt.strftime('%-I:%M %p CST'),
            'venue':        venue,
            'city':         city,
        })

    print(f'\nInserting {len(rows)} matches into Supabase …')
    ok = 0
    for start in range(0, len(rows), 20):
        batch = rows[start:start + 20]
        if sb_upsert('matches', batch):
            ok += len(batch)
        print(f'  {min(start + 20, len(rows))}/{len(rows)} done')
        time.sleep(0.3)

    print(f'\n  {ok}/{len(rows)} matches inserted.')

    # Write SQL backup in case direct insert had issues
    with open('matches_backup.sql', 'w') as f:
        f.write('-- FIFA 2026 Matches backup — paste into Supabase SQL Editor if needed\n\n')
        f.write('INSERT INTO public.matches\n'
                '  (match_number, fd_id, stage, group_name, team1, team2, match_date, match_time, venue, city)\nVALUES\n')
        vals = []
        for r in rows:
            gn = f"'{r['group_name']}'" if r['group_name'] else 'NULL'
            t1 = r['team1'].replace("'", "''")
            t2 = r['team2'].replace("'", "''")
            v  = r['venue'].replace("'", "''")
            vals.append(
                f"  ({r['match_number']}, {r['fd_id']}, '{r['stage']}', {gn}, "
                f"'{t1}', '{t2}', '{r['match_date']}', '{r['match_time']}', '{v}', '{r['city']}')"
            )
        f.write(',\n'.join(vals))
        f.write('\nON CONFLICT (match_number) DO UPDATE SET\n'
                '  fd_id=EXCLUDED.fd_id, team1=EXCLUDED.team1, team2=EXCLUDED.team2,\n'
                '  match_date=EXCLUDED.match_date, match_time=EXCLUDED.match_time;\n')
    print('  SQL backup → matches_backup.sql\n')


if __name__ == '__main__':
    main()
