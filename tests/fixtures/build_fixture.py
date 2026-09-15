"""Generate the offline fixture: JSON files shaped like the public FPL API.

Run `python tests/fixtures/build_fixture.py` to regenerate. Values are
deterministic and invented; only the *shapes* mirror the real endpoints.

Fixture facts the tests rely on:
  - 38 events; GW1 deadline 2026-08-15T10:00:00Z, then weekly Saturdays.
  - GW6 is current, GW7 is next (deadline 2026-09-26T10:00:00Z).
  - GW7 is a double for team 1 (two fixtures) and a blank for team 20.
  - Entry 12345 used the wildcard in GW3.
  - Two H2H leagues: 1001 (entry is 2nd, next opponent entry 22222) and 1002.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM_ID = 12345
N_TEAMS = 20
CURRENT_GW = 6
NEXT_GW = 7
GW1_DEADLINE = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)

TEAM_NAMES = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Leeds", "Liverpool",
    "Man City", "Man Utd", "Newcastle", "Nott'm Forest", "Sunderland",
    "Spurs", "West Ham", "Wolves",
]
SHORT = [
    "ARS", "AVL", "BOU", "BRE", "BHA", "BUR", "CHE", "CRY", "EVE", "FUL",
    "LEE", "LIV", "MCI", "MUN", "NEW", "NFO", "SUN", "TOT", "WHU", "WOL",
]


def z(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def events():
    out = []
    for i in range(1, 39):
        deadline = GW1_DEADLINE + timedelta(weeks=i - 1)
        out.append({
            "id": i,
            "name": f"Gameweek {i}",
            "deadline_time": z(deadline),
            "finished": i < CURRENT_GW,
            "data_checked": i < CURRENT_GW,
            "is_previous": i == CURRENT_GW - 1,
            "is_current": i == CURRENT_GW,
            "is_next": i == NEXT_GW,
            "average_entry_score": 55 if i <= CURRENT_GW else 0,
            "highest_score": 120 if i <= CURRENT_GW else None,
            "chip_plays": [],
            "most_selected": None,
            "most_transferred_in": None,
            "top_element": None,
        })
    return out


def teams():
    out = []
    for i in range(1, N_TEAMS + 1):
        # strength 2..5 spread across the table
        strength = 2 + ((i * 7) % 4)
        out.append({
            "id": i,
            "code": 100 + i,
            "name": TEAM_NAMES[i - 1],
            "short_name": SHORT[i - 1],
            "strength": strength,
            "strength_overall_home": 1000 + 50 * strength,
            "strength_overall_away": 980 + 50 * strength,
            "strength_attack_home": 1000 + 50 * strength,
            "strength_attack_away": 980 + 50 * strength,
            "strength_defence_home": 1000 + 50 * strength,
            "strength_defence_away": 980 + 50 * strength,
        })
    return out


def element_types():
    return [
        {"id": 1, "singular_name_short": "GKP", "plural_name": "Goalkeepers",
         "squad_select": 2, "squad_min_play": 1, "squad_max_play": 1},
        {"id": 2, "singular_name_short": "DEF", "plural_name": "Defenders",
         "squad_select": 5, "squad_min_play": 3, "squad_max_play": 5},
        {"id": 3, "singular_name_short": "MID", "plural_name": "Midfielders",
         "squad_select": 5, "squad_min_play": 2, "squad_max_play": 5},
        {"id": 4, "singular_name_short": "FWD", "plural_name": "Forwards",
         "squad_select": 3, "squad_min_play": 1, "squad_max_play": 3},
    ]


# (id, web_name, team, element_type, price_tenths, status, form, ep_next, event_points, news)
PLAYERS = [
    (1, "Raya", 1, 1, 55, "a", "4.2", "4.5", 6, ""),
    (2, "Sels", 16, 1, 45, "a", "2.8", "3.0", 2, ""),
    (3, "Gabriel", 1, 2, 62, "a", "5.1", "5.2", 8, ""),
    (4, "Van Dijk", 12, 2, 60, "a", "4.4", "4.8", 6, ""),
    (5, "Gvardiol", 13, 2, 60, "d", "3.0", "2.1", 0, "Knock - 75% chance of playing"),
    (6, "Cucurella", 7, 2, 61, "a", "3.9", "4.0", 2, ""),
    (7, "Tarkowski", 9, 2, 55, "a", "2.5", "2.9", 1, ""),
    (8, "Salah", 12, 3, 145, "a", "8.6", "8.9", 13, ""),
    (9, "Palmer", 7, 3, 105, "a", "6.1", "6.4", 7, ""),
    (10, "Saka", 1, 3, 100, "i", "0.0", "0.0", 0, "Hamstring injury - Expected back 10 Oct"),
    (11, "Bruno", 14, 3, 90, "a", "5.5", "5.9", 9, ""),
    (12, "Mbeumo", 14, 3, 80, "a", "5.0", "5.3", 4, ""),
    (13, "Haaland", 13, 4, 142, "a", "9.2", "9.5", 15, ""),
    (14, "Isak", 12, 4, 105, "a", "5.8", "6.2", 6, ""),
    (15, "Wood", 16, 4, 75, "a", "4.1", "4.4", 2, ""),
    # not in the squad
    (16, "Watkins", 2, 4, 90, "a", "4.9", "5.1", 5, ""),
    (17, "Rogers", 2, 3, 70, "a", "4.0", "4.2", 2, ""),
    (18, "Pope", 15, 1, 50, "a", "3.5", "3.7", 3, ""),
    (19, "Munoz", 8, 2, 55, "a", "3.6", "3.8", 6, ""),
    (20, "Ekitike", 12, 4, 85, "s", "0.0", "0.0", 0, "Suspended until 03 Oct"),
]


def elements():
    out = []
    for pid, name, team, etype, price, status, form, ep_next, ev_pts, news in PLAYERS:
        out.append({
            "id": pid,
            "code": 5000 + pid,
            "web_name": name,
            "first_name": name,
            "second_name": name,
            "team": team,
            "element_type": etype,
            "now_cost": price,
            "status": status,
            "news": news,
            "chance_of_playing_next_round": None if status == "a" else (75 if status == "d" else 0),
            "form": form,
            "ep_next": ep_next,
            "ep_this": ep_next,
            "event_points": ev_pts,
            "total_points": int(float(form) * CURRENT_GW),
            "points_per_game": form,
            "selected_by_percent": "20.0",
            "minutes": 90 * CURRENT_GW,
        })
    return out


def bootstrap():
    return {
        "events": events(),
        "teams": teams(),
        "element_types": element_types(),
        "elements": elements(),
        "total_players": 11000000,
    }


def fixtures():
    """Round-robin-ish schedule. GW7: team 1 doubles, team 20 blanks."""
    out = []
    fid = 1
    for gw in range(1, 39):
        deadline = GW1_DEADLINE + timedelta(weeks=gw - 1)
        ids = list(range(1, N_TEAMS + 1))
        # rotate so each team meets different opponents
        rot = ids[1:]
        k = (gw - 1) % len(rot)
        rot = rot[k:] + rot[:k]
        order = [ids[0]] + rot
        pairs = [(order[i], order[N_TEAMS - 1 - i]) for i in range(N_TEAMS // 2)]
        if gw == NEXT_GW:
            # Team 20's match is postponed; team 1 plays that rearranged game too.
            pairs = [p for p in pairs if 20 not in p]
            partner = next(p for p in pairs if 1 in p)
            other = partner[0] if partner[1] == 1 else partner[1]
            # give team 1 a second fixture against a team not already paired with it
            spare = next(t for t in range(2, N_TEAMS) if t not in (other,) and all(t not in p for p in pairs))
            pairs.append((spare, 1))
        for h, a in pairs:
            finished = gw < CURRENT_GW
            out.append({
                "id": fid,
                "code": 900000 + fid,
                "event": gw,
                "finished": finished,
                "finished_provisional": finished,
                "kickoff_time": z(deadline + timedelta(hours=5)),
                "minutes": 90 if finished else 0,
                "started": finished,
                "team_h": h,
                "team_a": a,
                "team_h_score": 1 if finished else None,
                "team_a_score": 1 if finished else None,
                "team_h_difficulty": 2 + ((a * 3) % 4),
                "team_a_difficulty": 2 + ((h * 5) % 4),
                "stats": [],
            })
            fid += 1
    # a postponed fixture with no event yet (the API does this)
    out.append({
        "id": fid, "code": 900000 + fid, "event": None, "finished": False,
        "finished_provisional": False, "kickoff_time": None, "minutes": 0, "started": None,
        "team_h": 20, "team_a": 19, "team_h_score": None, "team_a_score": None,
        "team_h_difficulty": 3, "team_a_difficulty": 3, "stats": [],
    })
    return out


def entry():
    return {
        "id": TEAM_ID,
        "joined_time": "2026-07-20T09:00:00Z",
        "started_event": 1,
        "favourite_team": 12,
        "player_first_name": "Fixture",
        "player_last_name": "Manager",
        "player_region_id": 229,
        "player_region_name": "England",
        "player_region_iso_code_short": "EN",
        "summary_overall_points": 331,
        "summary_overall_rank": 812345,
        "summary_event_points": 61,
        "summary_event_rank": 1500000,
        "current_event": CURRENT_GW,
        "leagues": {"classic": [], "h2h": [
            {"id": 1001, "name": "Office H2H", "entry_rank": 2, "entry_last_rank": 3},
            {"id": 1002, "name": "Old Boys H2H", "entry_rank": 5, "entry_last_rank": 5},
        ], "cup": None},
        "name": "Fixture FC",
        "name_change_blocked": False,
        "kit": None,
        "last_deadline_bank": 12,
        "last_deadline_value": 1003,
        "last_deadline_total_transfers": 4,
    }


def history():
    current = []
    total = 0
    for gw in range(1, CURRENT_GW + 1):
        pts = 50 + 3 * gw
        total += pts
        current.append({
            "event": gw, "points": pts, "total_points": total,
            "rank": 900000 + gw * 1000, "rank_sort": 900000 + gw * 1000,
            "overall_rank": 812345, "bank": 12, "value": 1003,
            "event_transfers": 1 if gw > 1 else 0,
            "event_transfers_cost": 0, "points_on_bench": 4,
        })
    return {
        "current": current,
        "past": [{"season_name": "2025/26", "total_points": 2301, "rank": 350000}],
        "chips": [{"name": "wildcard", "time": "2026-08-28T18:00:00Z", "event": 3}],
    }


def picks():
    squad = [(pid, pos) for pos, pid in enumerate(range(1, 16), start=1)]
    # order: GK, DEF x4, MID x4, FWD x2 starting; bench GK2, DEF5, MID5, FWD3
    starting = [1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14]
    bench = [2, 7, 12, 15]
    out = []
    for pos, pid in enumerate(starting + bench, start=1):
        out.append({
            "element": pid,
            "position": pos,
            "multiplier": 2 if pid == 13 else (1 if pos <= 11 else 0),
            "is_captain": pid == 13,
            "is_vice_captain": pid == 8,
        })
    return {
        "active_chip": None,
        "automatic_subs": [],
        "entry_history": {
            "event": CURRENT_GW, "points": 61, "total_points": 331, "rank": 1500000,
            "rank_sort": 1500000, "overall_rank": 812345, "bank": 12, "value": 1003,
            "event_transfers": 1, "event_transfers_cost": 0, "points_on_bench": 4,
        },
        "picks": out,
    }


H2H_ENTRIES = {
    TEAM_ID: ("Fixture FC", "Fixture Manager"),
    22222: ("Bench Warmers", "Second Manager"),
    33333: ("Route One", "Third Manager"),
    44444: ("Park The Bus", "Fourth Manager"),
    55555: ("Tiki Taka", "Fifth Manager"),
    66666: ("Long Ball FC", "Sixth Manager"),
}


def h2h_matches(league_id: int):
    others = [e for e in H2H_ENTRIES if e != TEAM_ID]
    results = []
    mid = league_id * 100
    for gw in range(1, 39):
        opp = others[(gw + league_id) % len(others)]
        finished = gw <= CURRENT_GW
        my_pts = 50 + 3 * gw if finished else 0
        opp_pts = 48 + 2 * gw if finished else 0
        results.append({
            "id": mid + gw,
            "entry_1_entry": TEAM_ID,
            "entry_1_name": H2H_ENTRIES[TEAM_ID][0],
            "entry_1_player_name": H2H_ENTRIES[TEAM_ID][1],
            "entry_1_points": my_pts,
            "entry_1_win": 1 if finished and my_pts > opp_pts else 0,
            "entry_1_draw": 1 if finished and my_pts == opp_pts else 0,
            "entry_1_loss": 1 if finished and my_pts < opp_pts else 0,
            "entry_1_total": 0,
            "entry_2_entry": opp,
            "entry_2_name": H2H_ENTRIES[opp][0],
            "entry_2_player_name": H2H_ENTRIES[opp][1],
            "entry_2_points": opp_pts,
            "entry_2_win": 1 if finished and opp_pts > my_pts else 0,
            "entry_2_draw": 1 if finished and my_pts == opp_pts else 0,
            "entry_2_loss": 1 if finished and opp_pts < my_pts else 0,
            "entry_2_total": 0,
            "is_knockout": False,
            "league": league_id,
            "winner": TEAM_ID if finished else None,
            "seed_value": None,
            "event": gw,
            "tiebreak": None,
            "is_bye": False,
        })
    return {
        "has_next": False,
        "page": 1,
        "results": results,
    }


def h2h_standings(league_id: int):
    order = list(H2H_ENTRIES)
    # league 1001: we are 2nd; league 1002: we are 5th
    if league_id == 1001:
        order = [22222, TEAM_ID, 33333, 44444, 55555, 66666]
    else:
        order = [33333, 44444, 55555, 66666, TEAM_ID, 22222]
    results = []
    for rank, e in enumerate(order, start=1):
        pts = 18 - 3 * (rank - 1)  # H2H league points, 3 per win
        results.append({
            "id": league_id * 10 + rank,
            "division": league_id,
            "entry": e,
            "player_name": H2H_ENTRIES[e][1],
            "rank": rank,
            "last_rank": rank,
            "rank_sort": rank,
            "total": pts,
            "entry_name": H2H_ENTRIES[e][0],
            "matches_played": CURRENT_GW,
            "matches_won": pts // 3,
            "matches_drawn": 0,
            "matches_lost": CURRENT_GW - pts // 3,
            "points_for": 331 - 10 * (rank - 1),  # FPL points scored
        })
    name = "Office H2H" if league_id == 1001 else "Old Boys H2H"
    return {
        "league": {"id": league_id, "name": name, "created": "2026-07-21T10:00:00Z",
                   "closed": True, "max_entries": None, "league_type": "x",
                   "scoring": "h", "admin_entry": 22222, "start_event": 1,
                   "code_privacy": "p", "has_cup": False, "cup_league": None, "rank": None},
        "new_entries": {"has_next": False, "page": 1, "results": []},
        "standings": {"has_next": False, "page": 1, "results": results},
    }


def write(name: str, payload) -> None:
    with open(HERE / name, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")


def main() -> None:
    write("bootstrap-static.json", bootstrap())
    write("fixtures.json", fixtures())
    write("entry.json", entry())
    write("entry-history.json", history())
    write("picks.json", picks())
    for lid in (1001, 1002):
        write(f"h2h-matches-{lid}.json", h2h_matches(lid))
        write(f"h2h-standings-{lid}.json", h2h_standings(lid))


if __name__ == "__main__":
    main()
