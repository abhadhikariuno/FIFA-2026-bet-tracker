"""
poll_results.py — Daily daemon that auto-fetches FIFA 2026 match results,
                  scores, and keeps the knockout bracket up to date.

Logic:
  • Every minute, check today's unresolved matches.
  • 2h30m after kickoff → query football-data.org for the result.
  • On FINISHED: post winner + home/away goals to Supabase automatically.
  • After every group stage result: check if the group is complete (6/6 done).
    If so, re-fetch all WC matches from football-data.org and upsert team
    names — this fills in TBD slots in R32 as soon as FIFA publishes the bracket.
  • 11 PM CST sweep catches any matches still unresolved at end of day.

Setup:
    pip install requests pytz
    python poll_results.py

Keep this running in the background on match days.
"""

import time, requests
from datetime import datetime, timedelta
import pytz

# ── CONFIG ───────────────────────────────────────────────────
import os
FD_API_KEY   = os.environ['FD_API_KEY']
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
FD_BASE      = 'https://api.football-data.org/v4'
CT           = pytz.timezone('America/Chicago')

POST_DELAY_HOURS = 2.5  # hours after kickoff before first result check
END_OF_DAY_HOUR  = 23   # 11 PM CST — final sweep
# ─────────────────────────────────────────────────────────────

STAKE_MAP = {
    'Group': 10, 'R32': 15, 'R16': 20,
    'QF': 30, 'SF': 50, '3rd': 30, 'Final': 100,
}

STAGE_MAP = {
    'GROUP_STAGE':    'Group',
    'LAST_32':        'R32',
    'LAST_16':        'R16',
    'QUARTER_FINALS': 'QF',
    'SEMI_FINALS':    'SF',
    'THIRD_PLACE':    '3rd',
    'FINAL':          'Final',
}


# ── API helpers ──────────────────────────────────────────────

def fd_get(path):
    r = requests.get(f'{FD_BASE}{path}', headers={'X-Auth-Token': FD_API_KEY})
    if r.status_code == 429:
        wait = int(r.headers.get('X-RequestCounter-Reset', 60))
        print(f'  [rate limit] waiting {wait}s …')
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


def sb_get(table, params=None):
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/{table}',
        headers=sb_headers(),
        params=params or {},
    )
    r.raise_for_status()
    return r.json()


def sb_upsert(table, data, on_conflict):
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/{table}',
        headers={**sb_headers(), 'Prefer': 'resolution=merge-duplicates,return=minimal'},
        params={'on_conflict': on_conflict},
        json=data,
    )
    return r.ok


# ── Core logic ───────────────────────────────────────────────

def get_todays_pending():
    today   = datetime.now(CT).strftime('%Y-%m-%d')
    matches = sb_get('matches', {'match_date': f'eq.{today}', 'select': '*'})
    if not matches:
        return []
    existing = {r['match_id'] for r in sb_get('results', {'select': 'match_id'})}
    return [m for m in matches if m['id'] not in existing]


def fetch_fd_result(fd_id):
    """Return (winner, home_goals, away_goals, status) from football-data.org."""
    data   = fd_get(f'/matches/{fd_id}')
    status = data.get('status', '')

    if status != 'FINISHED':
        return None, None, None, status

    score      = data.get('score', {})
    full_time  = score.get('fullTime', {})
    home_goals = full_time.get('home')
    away_goals = full_time.get('away')
    outcome    = score.get('winner')   # HOME_TEAM | AWAY_TEAM | DRAW
    home_name  = data['homeTeam']['name']
    away_name  = data['awayTeam']['name']

    if outcome == 'HOME_TEAM':
        winner = home_name
    elif outcome == 'AWAY_TEAM':
        winner = away_name
    elif outcome == 'DRAW':
        winner = 'draw'
    else:
        return None, None, None, status

    return winner, home_goals, away_goals, status


def kickoff_ct(match):
    date_str = match['match_date']
    time_str = (match.get('match_time') or '12:00 PM CST').replace(' CST', '').replace(' ET', '').strip()
    naive    = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %I:%M %p')
    return CT.localize(naive)


def process_match(match):
    fd_id = match.get('fd_id')
    if not fd_id:
        print(f'  [{match["team1"]} vs {match["team2"]}] no fd_id — skipping')
        return False

    winner, home_goals, away_goals, status = fetch_fd_result(fd_id)
    if winner is None:
        print(f'  [{match["team1"]} vs {match["team2"]}] status={status}')
        return False

    stake   = STAKE_MAP.get(match['stage'], 10)
    payload = {
        'match_id':   match['id'],
        'winner':     winner,
        'stake':      stake,
        'posted_at':  datetime.now(CT).isoformat(),
    }
    if home_goals is not None:
        payload['home_goals'] = home_goals
        payload['away_goals'] = away_goals

    ok    = sb_upsert('results', payload, 'match_id')
    score_str = f'{home_goals}–{away_goals}' if home_goals is not None else '?–?'
    label = f'DRAW {score_str}' if winner == 'draw' else f'{winner} {score_str}'
    print(f'  [{match["team1"]} vs {match["team2"]}] {label} — {"✓" if ok else "✗"}')

    # If this was a group stage match, check if the group is now complete
    if ok and match['stage'] == 'Group' and match.get('group_name'):
        check_group_complete(match['group_name'])

    return ok


def check_group_complete(group_name):
    """If all 6 group matches are done, refresh the full bracket from football-data.org."""
    group_matches = sb_get('matches', {
        'stage':      'eq.Group',
        'group_name': f'eq.{group_name}',
        'select':     'id',
    })
    match_ids  = [m['id'] for m in group_matches]
    if not match_ids:
        return

    results = sb_get('results', {'select': 'match_id'})
    done    = {r['match_id'] for r in results}
    pending = [mid for mid in match_ids if mid not in done]

    if pending:
        return  # group not complete yet

    print(f'\n  Group {group_name} complete — refreshing bracket …')
    refresh_bracket()


def refresh_bracket():
    """Re-fetch all WC matches and upsert team names to fill in TBD slots."""
    try:
        data    = fd_get('/competitions/WC/matches')
        matches = data.get('matches', [])
        rows    = []
        for i, m in enumerate(matches, 1):
            t1 = m['homeTeam'].get('name') or 'TBD'
            t2 = m['awayTeam'].get('name') or 'TBD'
            if t1 == 'TBD' and t2 == 'TBD':
                continue  # nothing to update yet
            rows.append({
                'match_number': i,
                'fd_id':        m['id'],
                'team1':        t1,
                'team2':        t2,
            })

        # Batch upsert in groups of 20
        updated = 0
        for start in range(0, len(rows), 20):
            batch = rows[start:start + 20]
            if sb_upsert('matches', batch, 'match_number'):
                updated += len(batch)
            time.sleep(0.2)

        print(f'  Bracket refresh: {updated} matches updated.\n')
    except Exception as e:
        print(f'  Bracket refresh failed: {e}\n')


def run_once():
    """Single-pass check — designed for scheduled execution (GitHub Actions, cron, etc.)."""
    now     = datetime.now(CT)
    print(f'FIFA poller run — {now.strftime("%Y-%m-%d %H:%M CST")}')
    pending = get_todays_pending()

    if not pending:
        print('  No pending matches today.')
        return

    for match in pending:
        try:
            ko       = kickoff_ct(match)
            check_at = ko + timedelta(hours=POST_DELAY_HOURS)
            if now >= check_at:
                process_match(match)
            else:
                wait_min = int((check_at - now).total_seconds() / 60)
                print(f'  [{match["team1"]} vs {match["team2"]}] checking in {wait_min} min')
        except Exception as e:
            print(f'  Error: {e}')

    # End-of-day sweep for anything still unresolved
    if now.hour >= END_OF_DAY_HOUR:
        print('End-of-day sweep …')
        for match in get_todays_pending():
            try:
                process_match(match)
            except Exception as e:
                print(f'  EOD error: {e}')


def run():
    print(f'FIFA 2026 result poller started — {datetime.now(CT).strftime("%Y-%m-%d %H:%M CST")}')
    print(f'  Checking results {POST_DELAY_HOURS}h after kickoff, every 60s.\n')

    eod_swept = False

    while True:
        now     = datetime.now(CT)
        pending = get_todays_pending()

        if not pending:
            print(f'[{now.strftime("%H:%M")}] No pending matches today.')
        else:
            for match in pending:
                try:
                    ko       = kickoff_ct(match)
                    check_at = ko + timedelta(hours=POST_DELAY_HOURS)
                    if now >= check_at:
                        process_match(match)
                    else:
                        wait_min = int((check_at - now).total_seconds() / 60)
                        print(f'  [{match["team1"]} vs {match["team2"]}] '
                              f'kickoff {ko.strftime("%H:%M")} — checking in {wait_min} min')
                except Exception as e:
                    print(f'  Error processing match {match.get("id")}: {e}')

        # End-of-day sweep
        if now.hour >= END_OF_DAY_HOUR and not eod_swept:
            print(f'\n[{now.strftime("%H:%M")}] End-of-day sweep …')
            for match in get_todays_pending():
                try:
                    process_match(match)
                except Exception as e:
                    print(f'  EOD error: {e}')
            eod_swept = True
            print('  EOD sweep done.\n')

        if now.hour == 0:
            eod_swept = False

        time.sleep(60)


if __name__ == '__main__':
    import sys
    if '--once' in sys.argv:
        run_once()
    else:
        run()
