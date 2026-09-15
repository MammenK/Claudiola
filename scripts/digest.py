"""Write brief.md: the data the routine needs, as tables, with no analysis.

Layout of brief.md (the routine reads only the header at its gate, so the
header stays at the very top):

  <ISO timestamp>
  gameweek: 7
  deadline: 2026-09-26T10:00:00Z
  hours_to_deadline: 27.0
  chips_remaining: freehit, bboost, 3xc
  gameweeks_to_expiry: 12
  is_blank: true
  is_double: true

  ...sections...

Then state/overrides.md appended verbatim if it exists locally (it is
gitignored, so it is absent in CI and simply skipped).

This script WRITES the digest. It never prints it: overrides content would
otherwise land in the public Actions log. Only a one-line status goes to
stderr.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from scripts.common import (
    CHIP_LABELS,
    CHIPS,
    FILE_BOOTSTRAP,
    FILE_ENTRY,
    FILE_FIXTURES,
    FILE_HISTORY,
    FILE_PICKS,
    REPO_ROOT,
    blank_double_flags,
    chips_remaining,
    chips_used,
    data_dir_from_env,
    file_h2h_matches,
    file_h2h_standings,
    gameweeks_to_expiry,
    h2h_league_ids,
    half_of,
    iso_z,
    last_event_id,
    load_config,
    load_json,
    load_json_optional,
    next_event,
    parse_iso,
    setup_logging,
    utcnow,
)

log = logging.getLogger("digest")

DEFAULT_OUT = REPO_ROOT / "brief.md"
DEFAULT_OVERRIDES = REPO_ROOT / "state" / "overrides.md"
WORD_LIMIT = 800
FDR_HORIZON = 5

STATUS_FLAG = {
    "a": "OK",
    "d": "DOUBT",
    "i": "INJ",
    "s": "SUSP",
    "u": "OUT",
    "n": "N/A",
}


# --- small formatting helpers ------------------------------------------------

def table(headers: list[str], rows: list[list]) -> str:
    def cell(v) -> str:
        return "" if v is None else str(v).replace("|", "\\|")

    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(lines)


def price(now_cost: int) -> str:
    return f"{now_cost / 10:.1f}"


def fnum(value) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "-"


def yesno(flag: bool) -> str:
    return "true" if flag else "false"


def word_count(text: str) -> int:
    return len(text.split())


# --- data shaping ------------------------------------------------------------

def index_by_id(items: list[dict]) -> dict[int, dict]:
    return {item["id"]: item for item in items}


def team_fixture_cells(fixtures: list[dict], teams: dict, team_id: int, gw: int, horizon: int) -> list[str]:
    """One cell per gameweek gw..gw+horizon-1: 'OPP(H)3', 'A+B' for doubles, '-' for blanks."""
    cells = []
    for g in range(gw, gw + horizon):
        parts = []
        for f in fixtures:
            if f.get("event") != g:
                continue
            if f["team_h"] == team_id:
                parts.append(f"{teams[f['team_a']]['short_name']}(H){f['team_h_difficulty']}")
            elif f["team_a"] == team_id:
                parts.append(f"{teams[f['team_h']]['short_name']}(A){f['team_a_difficulty']}")
        cells.append(" + ".join(parts) if parts else "-")
    return cells


def status_flag(el: dict) -> str:
    flag = STATUS_FLAG.get(el.get("status"), el.get("status", "?"))
    chance = el.get("chance_of_playing_next_round")
    if flag != "OK" and chance is not None:
        flag = f"{flag} {chance}%"
    return flag


def squad_rows(picks: dict, elements: dict, teams: dict, types: dict, fixtures: list, gw: int) -> list[dict]:
    rows = []
    for p in sorted(picks["picks"], key=lambda p: p["position"]):
        el = elements[p["element"]]
        name = el["web_name"]
        if p.get("is_captain"):
            name += " (C)"
        elif p.get("is_vice_captain"):
            name += " (V)"
        rows.append({
            "position": p["position"],
            "id": el["id"],
            "name": name,
            "pos": types[el["element_type"]]["singular_name_short"],
            "team": teams[el["team"]]["short_name"],
            "price": price(el["now_cost"]),
            "status": status_flag(el),
            "news": el.get("news") or "",
            "form": el.get("form"),
            "ep_next": el.get("ep_next"),
            "event_points": el.get("event_points"),
            "fdr": team_fixture_cells(fixtures, teams, el["team"], gw, FDR_HORIZON),
            "starter": p["position"] <= 11,
            "raw_status": el.get("status"),
        })
    return rows


def captain_candidates(rows: list[dict], n: int = 3) -> list[dict]:
    fit = [r for r in rows if r["starter"] and r["raw_status"] == "a"]
    fit.sort(key=lambda r: (-float(r["ep_next"] or 0), -float(r["form"] or 0)))
    return fit[:n]


def h2h_section(cfg: dict, entry: dict, data_dir: Path, gw: int) -> tuple[list[str], list[list]]:
    """Rows for the H2H table: one per league."""
    team_id = int(cfg["team_id"])
    rows = []
    for lid in h2h_league_ids(cfg, entry):
        matches = load_json_optional(data_dir, file_h2h_matches(lid))
        standings = load_json_optional(data_dir, file_h2h_standings(lid))
        if matches is None or standings is None:
            log.warning("h2h league %d: data missing, skipped", lid)
            continue
        league_name = (standings.get("league") or {}).get("name", str(lid))
        by_entry = {r.get("entry"): r for r in (standings.get("standings") or {}).get("results", [])}
        me = by_entry.get(team_id)

        opp_id = None
        for m in matches.get("results", []):
            if m.get("event") != gw:
                continue
            if m.get("entry_1_entry") == team_id:
                opp_id = m.get("entry_2_entry")
            elif m.get("entry_2_entry") == team_id:
                opp_id = m.get("entry_1_entry")
            break
        opp = by_entry.get(opp_id) if opp_id is not None else None

        # Standings rows: `total` is the H2H league points (3 per win),
        # `points_for` the FPL points scored. Use .get so an unexpected shape
        # degrades to "-" rather than crashing the brief.
        my_pts = me.get("total") if me else None
        opp_pts = opp.get("total") if opp else None
        rows.append([
            league_name,
            me.get("rank", "-") if me else "-",
            my_pts if my_pts is not None else "-",
            opp.get("entry_name", str(opp_id)) if opp else ("bye" if opp_id is None else str(opp_id)),
            opp.get("rank", "-") if opp else "-",
            opp_pts if opp_pts is not None else "-",
            (my_pts - opp_pts) if (my_pts is not None and opp_pts is not None) else "-",
            opp.get("points_for", "-") if opp else "-",
        ])
    headers = ["League", "My rank", "My H2H pts", "GW opponent", "Opp rank", "Opp H2H pts", "Gap", "Opp FPL total"]
    return headers, rows


# --- the digest --------------------------------------------------------------

def build_brief(cfg: dict, data_dir: Path, now: datetime, overrides_path: Path | None) -> str:
    bootstrap = load_json(data_dir, FILE_BOOTSTRAP)
    fixtures = load_json(data_dir, FILE_FIXTURES)
    entry = load_json(data_dir, FILE_ENTRY)
    history = load_json(data_dir, FILE_HISTORY)
    picks = load_json_optional(data_dir, FILE_PICKS)

    ev = next_event(bootstrap)
    if ev is None:
        raise SystemExit("no upcoming gameweek; nothing to digest")
    gw = ev["id"]
    deadline = parse_iso(ev["deadline_time"])
    hours = round((deadline - now).total_seconds() / 3600, 1)
    half_gw = int(cfg["half_deadline_gw"])
    remaining = chips_remaining(history, gw, half_gw)
    expiry = gameweeks_to_expiry(gw, half_gw, last_event_id(bootstrap))
    is_blank, is_double = blank_double_flags(bootstrap, fixtures, gw)

    elements = index_by_id(bootstrap["elements"])
    teams = index_by_id(bootstrap["teams"])
    types = index_by_id(bootstrap["element_types"])

    out: list[str] = []
    # Header block. Keep it first and machine-readable.
    out.append(iso_z(now))
    out.append(f"gameweek: {gw}")
    out.append(f"deadline: {iso_z(deadline)}")
    out.append(f"hours_to_deadline: {hours}")
    out.append("chips_remaining: " + (", ".join(remaining) if remaining else "none"))
    out.append(f"gameweeks_to_expiry: {expiry}")
    out.append(f"is_blank: {yesno(is_blank)}")
    out.append(f"is_double: {yesno(is_double)}")
    out.append("")
    out.append(f"# FPL brief — GW{gw} — {entry.get('name', 'entry ' + str(cfg['team_id']))}")
    out.append("")

    # Entry summary.
    out.append("## Entry")
    out.append(table(
        ["Overall pts", "Overall rank", "Last GW pts", "Bank £m", "Squad value £m"],
        [[
            entry.get("summary_overall_points"),
            entry.get("summary_overall_rank"),
            entry.get("summary_event_points"),
            price(entry.get("last_deadline_bank") or 0),
            price(entry.get("last_deadline_value") or 0),
        ]],
    ))
    out.append("")

    # Squad.
    fdr_headers = [f"GW{g}" for g in range(gw, gw + FDR_HORIZON)]
    if picks:
        picks_gw = (picks.get("entry_history") or {}).get("event", "?")
        rows = squad_rows(picks, elements, teams, types, fixtures, gw)
        out.append(f"## Squad (picks as of GW{picks_gw}; FDR 1 easy … 5 hard)")
        out.append(table(
            ["#", "Player", "Pos", "Team", "£m", "Status", "ep_next"] + fdr_headers,
            [[r["position"], r["name"], r["pos"], r["team"], r["price"], r["status"],
              fnum(r["ep_next"])] + r["fdr"] for r in rows],
        ))
        out.append("")

        flagged = [r for r in rows if r["raw_status"] != "a"]
        out.append("## Flags")
        if flagged:
            out.append(table(["Player", "Status", "News"], [[r["name"], r["status"], r["news"]] for r in flagged]))
        else:
            out.append("| Player | Status | News |\n|---|---|---|\n| none | | |")
        out.append("")

        # Bench strength.
        xi = [r for r in rows if r["starter"]]
        bench = [r for r in rows if not r["starter"]]
        xi_ep = sum(float(r["ep_next"] or 0) for r in xi)
        bench_ep = sum(float(r["ep_next"] or 0) for r in bench)
        out.append("## Bench strength (ep_next = FPL expected points next GW)")
        out.append(table(
            ["Bench", "Pos", "ep_next", "GW" + str(gw)],
            [[r["name"], r["pos"], fnum(r["ep_next"]), r["fdr"][0]] for r in bench],
        ))
        out.append("")
        out.append(table(
            ["XI ep_next", "Bench ep_next", "Bench / XI"],
            [[f"{xi_ep:.1f}", f"{bench_ep:.1f}", f"{(bench_ep / xi_ep) if xi_ep else 0:.2f}"]],
        ))
        out.append("")

        # Captain candidates.
        out.append("## Captain candidates (top 3 by ep_next among available starters)")
        out.append(table(
            ["Player", "ep_next", "Form", "Last GW pts", "GW" + str(gw)],
            [[r["name"], fnum(r["ep_next"]), fnum(r["form"]), r["event_points"], r["fdr"][0]]
             for r in captain_candidates(rows)],
        ))
        out.append("")
    else:
        out.append("## Squad")
        out.append("| note |\n|---|\n| no picks available yet (entry has no current gameweek) |")
        out.append("")

    # Chips.
    used = chips_used(history)
    used_by_half: dict[tuple[str, int], int] = {}
    for c in used:
        used_by_half[(c["name"], half_of(c["event"], half_gw))] = c["event"]
    this_half = half_of(gw, half_gw)
    out.append("## Chips")
    out.append(table(
        ["Chip", "Half 1 (GW1-%d)" % half_gw, "Half 2 (GW%d-%d)" % (half_gw + 1, last_event_id(bootstrap))],
        [[
            CHIP_LABELS[c],
            f"used GW{used_by_half[(c, 1)]}" if (c, 1) in used_by_half else ("available" if this_half == 1 else "expired"),
            f"used GW{used_by_half[(c, 2)]}" if (c, 2) in used_by_half else ("available" if this_half == 2 else "not yet"),
        ] for c in CHIPS],
    ))
    out.append("")

    # H2H.
    headers, h2h_rows = h2h_section(cfg, entry, data_dir, gw)
    out.append(f"## H2H (GW{gw})")
    if h2h_rows:
        out.append(table(headers, h2h_rows))
    else:
        out.append("| note |\n|---|\n| no H2H leagues configured |")
    out.append("")

    # Overrides: verbatim, local only.
    out.append("## Overrides")
    if overrides_path and overrides_path.exists():
        text = overrides_path.read_text(encoding="utf-8").rstrip()
        out.append(text if text else "_state/overrides.md is empty_")
        log.info("overrides appended (%d bytes)", len(text.encode("utf-8")))
    else:
        out.append("_none (state/overrides.md not present)_")
    out.append("")

    return "\n".join(out)


def write_brief(cfg: dict, data_dir: Path, out_path: Path, now: datetime, overrides_path: Path | None) -> Path:
    text = build_brief(cfg, data_dir, now, overrides_path)
    out_path.write_text(text, encoding="utf-8")
    words = word_count(text)
    log.info("wrote %s (%d bytes, %d words)", out_path.name, len(text.encode("utf-8")), words)
    if words > WORD_LIMIT:
        log.warning("brief is %d words, over the %d limit", words, WORD_LIMIT)
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="where to write (default: brief.md)")
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDES), help="local overrides file to append if present")
    parser.add_argument("--now", default=None, help="ISO timestamp for the brief (default: now, UTC)")
    args = parser.parse_args(argv)

    setup_logging()
    cfg = load_config(args.config) if args.config else load_config()
    data_dir = Path(args.data_dir) if args.data_dir else data_dir_from_env()
    now = parse_iso(args.now) if args.now else utcnow()
    write_brief(cfg, data_dir, Path(args.out), now, Path(args.overrides))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
