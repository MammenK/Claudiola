"""Decide whether a brief is worth producing this week.

Prints one JSON object to stdout:
  {proceed, reason, gw, hours_to_deadline, chips_remaining, is_blank, is_double}
and exits 1 when `proceed` is false, so `make brief` and the Actions job stop
before writing or committing anything.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from scripts.common import (
    FILE_BOOTSTRAP,
    FILE_FIXTURES,
    FILE_HISTORY,
    blank_double_flags,
    chips_remaining,
    data_dir_from_env,
    load_config,
    load_json,
    next_event,
    parse_iso,
    setup_logging,
    utcnow,
)


def evaluate(cfg: dict, bootstrap: dict, fixtures: list, history: dict, now: datetime) -> dict:
    """Pure gate decision. `now` must be timezone-aware."""
    max_hours = float(cfg["max_days_to_deadline"]) * 24
    ev = next_event(bootstrap)
    if ev is None:
        return {
            "proceed": False,
            "reason": "no upcoming gameweek (season finished or not yet scheduled)",
            "gw": None,
            "hours_to_deadline": None,
            "chips_remaining": [],
            "is_blank": False,
            "is_double": False,
        }

    gw = ev["id"]
    deadline = parse_iso(ev["deadline_time"])
    hours = round((deadline - now).total_seconds() / 3600, 1)
    is_blank, is_double = blank_double_flags(bootstrap, fixtures, gw)
    remaining = chips_remaining(history, gw, int(cfg["half_deadline_gw"]))

    if hours <= 0:
        proceed, reason = False, f"GW{gw} deadline has already passed"
    elif hours > max_hours:
        proceed, reason = False, (
            f"GW{gw} deadline is {hours:.1f}h away, more than "
            f"{cfg['max_days_to_deadline']} days"
        )
    else:
        proceed, reason = True, f"GW{gw} deadline in {hours:.1f}h"

    return {
        "proceed": proceed,
        "reason": reason,
        "gw": gw,
        "hours_to_deadline": hours,
        "chips_remaining": remaining,
        "is_blank": is_blank,
        "is_double": is_double,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--now", default=None, help="ISO timestamp to evaluate at (default: now, UTC)")
    args = parser.parse_args(argv)

    setup_logging()
    cfg = load_config(args.config) if args.config else load_config()
    data_dir = Path(args.data_dir) if args.data_dir else data_dir_from_env()
    now = parse_iso(args.now) if args.now else utcnow()

    result = evaluate(
        cfg,
        load_json(data_dir, FILE_BOOTSTRAP),
        load_json(data_dir, FILE_FIXTURES),
        load_json(data_dir, FILE_HISTORY),
        now,
    )
    print(json.dumps(result))
    return 0 if result["proceed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
