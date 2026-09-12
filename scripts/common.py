"""Shared helpers for the brief scripts.

Everything here is pure file / dict handling so it can be exercised by the
offline tests against the JSON fixture.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config.yaml"
DEFAULT_DATA_DIR = REPO_ROOT / "data"

# The four chips. FPL hands out one set per half of the season.
CHIPS = ("wildcard", "freehit", "bboost", "3xc")
CHIP_LABELS = {
    "wildcard": "Wildcard",
    "freehit": "Free Hit",
    "bboost": "Bench Boost",
    "3xc": "Triple Captain",
}

# Files written by fetch.py and read by gate.py / digest.py.
FILE_BOOTSTRAP = "bootstrap-static.json"
FILE_FIXTURES = "fixtures.json"
FILE_ENTRY = "entry.json"
FILE_HISTORY = "entry-history.json"
FILE_PICKS = "picks.json"


def file_h2h_matches(league_id: int) -> str:
    return f"h2h-matches-{league_id}.json"


def file_h2h_standings(league_id: int) -> str:
    return f"h2h-standings-{league_id}.json"


def setup_logging(level: int = logging.INFO) -> None:
    """Log to stderr only. Nothing here ever logs a response body."""
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp (FPL uses a trailing 'Z') to aware UTC."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_config(path: Path | str = DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    cfg.setdefault("h2h_league_ids", [])
    cfg.setdefault("half_deadline_gw", 19)
    cfg.setdefault("max_days_to_deadline", 8)
    if not cfg.get("team_id"):
        raise SystemExit("config.yaml: team_id must be set to your FPL entry id")
    return cfg


def data_dir_from_env(default: Path = DEFAULT_DATA_DIR) -> Path:
    return Path(os.environ.get("FPL_DATA_DIR", default))


def load_json(data_dir: Path | str, name: str):
    path = Path(data_dir) / name
    if not path.exists():
        raise SystemExit(f"missing {path} — run `make fetch` first")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_json_optional(data_dir: Path | str, name: str):
    path = Path(data_dir) / name
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --- gameweek / chip helpers -------------------------------------------------

def next_event(bootstrap: dict) -> dict | None:
    """The upcoming gameweek: the one whose deadline is next to pass."""
    for ev in bootstrap["events"]:
        if ev.get("is_next"):
            return ev
    return None


def current_event(bootstrap: dict) -> dict | None:
    for ev in bootstrap["events"]:
        if ev.get("is_current"):
            return ev
    return None


def last_event_id(bootstrap: dict) -> int:
    return max(ev["id"] for ev in bootstrap["events"])


def half_of(gw: int, half_deadline_gw: int) -> int:
    return 1 if gw <= half_deadline_gw else 2


def chips_used(history: dict) -> list[dict]:
    """[{name, event}] from the entry history, oldest first."""
    used = [{"name": c["name"], "event": c["event"]} for c in history.get("chips", [])]
    used.sort(key=lambda c: c["event"])
    return used


def chips_remaining(history: dict, gw: int, half_deadline_gw: int) -> list[str]:
    """Chips still available in the half of the season that `gw` falls in."""
    half = half_of(gw, half_deadline_gw)
    spent = {
        c["name"] for c in chips_used(history) if half_of(c["event"], half_deadline_gw) == half
    }
    return [c for c in CHIPS if c not in spent]


def gameweeks_to_expiry(gw: int, half_deadline_gw: int, last_gw: int) -> int:
    """Gameweeks left (inclusive of `gw`) before the current chip set expires.

    0 means `gw` is the final gameweek in which this half's chips can be played.
    """
    if gw <= half_deadline_gw:
        return half_deadline_gw - gw
    return last_gw - gw


def fixtures_for_event(fixtures: list[dict], gw: int) -> list[dict]:
    return [f for f in fixtures if f.get("event") == gw]


def fixture_counts_by_team(fixtures: list[dict], gw: int, team_ids) -> dict[int, int]:
    counts = {tid: 0 for tid in team_ids}
    for f in fixtures_for_event(fixtures, gw):
        counts[f["team_h"]] = counts.get(f["team_h"], 0) + 1
        counts[f["team_a"]] = counts.get(f["team_a"], 0) + 1
    return counts


def blank_double_flags(bootstrap: dict, fixtures: list[dict], gw: int) -> tuple[bool, bool]:
    """(is_blank, is_double) for the gameweek across the whole league."""
    counts = fixture_counts_by_team(fixtures, gw, [t["id"] for t in bootstrap["teams"]])
    is_blank = any(n == 0 for n in counts.values())
    is_double = any(n >= 2 for n in counts.values())
    return is_blank, is_double
