"""Write pool.csv: one row per player from bootstrap-static, slim enough to
commit weekly next to brief.md so the routine can name transfer targets.

Everything here is public FPL data. Like digest.py it writes a file and
prints nothing.
"""
from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

from scripts.common import FILE_BOOTSTRAP, REPO_ROOT, data_dir_from_env, load_json, setup_logging

log = logging.getLogger("pool")

DEFAULT_OUT = REPO_ROOT / "pool.csv"
COLUMNS = [
    "id", "web_name", "team", "pos", "price", "status", "chance", "news",
    "minutes", "starts", "total_points", "event_points", "form", "ep_next", "ppg",
    "selected_by", "xg", "xa", "xgi", "xgc", "clean_sheets", "defcon", "bonus", "bps",
    "cost_change_start", "transfers_in_event", "transfers_out_event",
]


def rows_from_bootstrap(bootstrap: dict) -> list[dict]:
    teams = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
    types = {t["id"]: t["singular_name_short"] for t in bootstrap["element_types"]}
    out = []
    for el in bootstrap["elements"]:
        out.append({
            "id": el["id"],
            "web_name": el["web_name"],
            "team": teams.get(el["team"], el["team"]),
            "pos": types.get(el["element_type"], el["element_type"]),
            "price": f"{el['now_cost'] / 10:.1f}",
            "status": el.get("status"),
            "chance": el.get("chance_of_playing_next_round"),
            "news": (el.get("news") or "").replace("\n", " "),
            "minutes": el.get("minutes"),
            "starts": el.get("starts"),
            "total_points": el.get("total_points"),
            "event_points": el.get("event_points"),
            "form": el.get("form"),
            "ep_next": el.get("ep_next"),
            "ppg": el.get("points_per_game"),
            "selected_by": el.get("selected_by_percent"),
            "xg": el.get("expected_goals"),
            "xa": el.get("expected_assists"),
            "xgi": el.get("expected_goal_involvements"),
            "xgc": el.get("expected_goals_conceded"),
            "clean_sheets": el.get("clean_sheets"),
            "defcon": el.get("defensive_contribution"),
            "bonus": el.get("bonus"),
            "bps": el.get("bps"),
            "cost_change_start": el.get("cost_change_start"),
            "transfers_in_event": el.get("transfers_in_event"),
            "transfers_out_event": el.get("transfers_out_event"),
        })
    out.sort(key=lambda r: (-(float(r["total_points"] or 0)), r["id"]))
    return out


def write_pool(data_dir: Path, out_path: Path) -> Path:
    rows = rows_from_bootstrap(load_json(data_dir, FILE_BOOTSTRAP))
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    log.info("wrote %s (%d bytes, %d players)", out_path.name, out_path.stat().st_size, len(rows))
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    setup_logging()
    data_dir = Path(args.data_dir) if args.data_dir else data_dir_from_env()
    write_pool(data_dir, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
