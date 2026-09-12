"""Pull the public FPL API into data/ as JSON, with a 6 hour local cache.

Every endpoint used is public and needs no authentication. The API returns
403 without a browser-like User-Agent, so one is always sent.

Logging policy (the Actions log is public): status codes, byte counts and
record counts only. Response bodies are never logged.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import requests

from scripts.common import (
    FILE_BOOTSTRAP,
    FILE_ENTRY,
    FILE_FIXTURES,
    FILE_HISTORY,
    FILE_PICKS,
    data_dir_from_env,
    file_h2h_matches,
    file_h2h_standings,
    load_config,
    setup_logging,
)

log = logging.getLogger("fetch")

BASE_URL = "https://fantasy.premierleague.com/api"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
CACHE_TTL_SECONDS = 6 * 60 * 60
TIMEOUT_SECONDS = 30


class FetchError(RuntimeError):
    """Raised for any non-200 response. Carries the status code, never the body."""

    def __init__(self, path: str, status: int):
        super().__init__(f"GET {path} -> HTTP {status}")
        self.path = path
        self.status = status


def record_count(payload) -> int:
    """A count worth logging for a payload, without touching its contents."""
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("elements", "picks", "current"):
            if isinstance(payload.get(key), list):
                return len(payload[key])
        inner = payload.get("standings") or payload.get("matches")
        if isinstance(inner, dict) and isinstance(inner.get("results"), list):
            return len(inner["results"])
        return len(payload)
    return 1


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return session


def is_fresh(path: Path, ttl: int = CACHE_TTL_SECONDS, now: float | None = None) -> bool:
    if not path.exists():
        return False
    age = (now if now is not None else time.time()) - path.stat().st_mtime
    return 0 <= age < ttl


def fetch_json(session: requests.Session, path: str):
    url = f"{BASE_URL}{path}"
    resp = session.get(url, timeout=TIMEOUT_SECONDS)
    size = len(resp.content or b"")
    if resp.status_code != 200:
        log.error("GET %s -> %s (%d bytes)", path, resp.status_code, size)
        raise FetchError(path, resp.status_code)
    try:
        payload = resp.json()
    except ValueError as exc:
        log.error("GET %s -> %s (%d bytes) not JSON", path, resp.status_code, size)
        raise FetchError(path, resp.status_code) from exc
    log.info("GET %s -> %s (%d bytes, %d records)", path, resp.status_code, size, record_count(payload))
    return payload


def fetch_to_file(session, path: str, dest: Path, force: bool = False):
    """Fetch `path` into `dest` unless a fresh cached copy exists. Returns the payload."""
    if not force and is_fresh(dest):
        log.info("cache hit %s (%d bytes)", dest.name, dest.stat().st_size)
        with open(dest, encoding="utf-8") as fh:
            return json.load(fh)
    payload = fetch_json(session, path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    log.info("wrote %s (%d bytes)", dest.name, dest.stat().st_size)
    return payload


def fetch_all(cfg: dict, data_dir: Path, session=None, force: bool = False) -> None:
    session = session or make_session()
    team_id = int(cfg["team_id"])
    data_dir.mkdir(parents=True, exist_ok=True)

    fetch_to_file(session, "/bootstrap-static/", data_dir / FILE_BOOTSTRAP, force)
    fetch_to_file(session, "/fixtures/", data_dir / FILE_FIXTURES, force)
    entry = fetch_to_file(session, f"/entry/{team_id}/", data_dir / FILE_ENTRY, force)
    fetch_to_file(session, f"/entry/{team_id}/history/", data_dir / FILE_HISTORY, force)

    gw = entry.get("current_event")
    if gw:
        fetch_to_file(session, f"/entry/{team_id}/event/{gw}/picks/", data_dir / FILE_PICKS, force)
    else:
        # Pre-season: the entry has no picks yet. Say so rather than write an empty file.
        log.warning("entry has no current_event; skipping picks")

    for lid in cfg.get("h2h_league_ids") or []:
        lid = int(lid)
        fetch_to_file(
            session,
            f"/leagues-h2h-matches/league/{lid}/?page=1&entry={team_id}",
            data_dir / file_h2h_matches(lid),
            force,
        )
        fetch_to_file(
            session,
            f"/leagues-h2h/{lid}/standings/",
            data_dir / file_h2h_standings(lid),
            force,
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--data-dir", default=None, help="where to write JSON (default: data/)")
    parser.add_argument("--force", action="store_true", help="ignore the 6h cache")
    args = parser.parse_args(argv)

    setup_logging()
    cfg = load_config(args.config) if args.config else load_config()
    data_dir = Path(args.data_dir) if args.data_dir else data_dir_from_env()
    try:
        fetch_all(cfg, data_dir, force=args.force)
    except FetchError as exc:
        log.error("fetch failed: %s", exc)
        return 2
    except requests.RequestException as exc:
        # Transport errors carry no body; the class name is enough for a public log.
        log.error("fetch failed: %s", type(exc).__name__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
