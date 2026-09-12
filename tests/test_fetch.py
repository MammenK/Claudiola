from __future__ import annotations

import json
import logging
import os
import time

import pytest

from scripts import fetch

SECRET_BODY = '{"elements": [], "token": "SHOULD-NEVER-BE-LOGGED"}'


class FakeResponse:
    def __init__(self, status: int, body: str):
        self.status_code = status
        self.content = body.encode("utf-8")

    def json(self):
        return json.loads(self.content)


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]):
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url, timeout=None):
        path = url[len(fetch.BASE_URL):]
        self.calls.append(path)
        return self.responses.get(path, FakeResponse(404, "not found"))


def test_403_raises_with_status_and_never_returns_empty():
    session = FakeSession({"/bootstrap-static/": FakeResponse(403, "<html>forbidden</html>")})
    with pytest.raises(fetch.FetchError) as exc:
        fetch.fetch_json(session, "/bootstrap-static/")
    assert exc.value.status == 403
    assert "403" in str(exc.value)


def test_logs_status_and_size_but_never_body(caplog):
    session = FakeSession({"/bootstrap-static/": FakeResponse(200, SECRET_BODY)})
    with caplog.at_level(logging.INFO, logger="fetch"):
        payload = fetch.fetch_json(session, "/bootstrap-static/")
    assert payload["token"] == "SHOULD-NEVER-BE-LOGGED"
    assert "200" in caplog.text
    assert str(len(SECRET_BODY)) in caplog.text
    assert "SHOULD-NEVER-BE-LOGGED" not in caplog.text


def test_error_log_never_contains_body(caplog):
    session = FakeSession({"/entry/1/": FakeResponse(500, "server said SHOULD-NEVER-BE-LOGGED")})
    with caplog.at_level(logging.DEBUG, logger="fetch"), pytest.raises(fetch.FetchError):
        fetch.fetch_json(session, "/entry/1/")
    assert "SHOULD-NEVER-BE-LOGGED" not in caplog.text


def test_cache_hit_within_ttl(tmp_path):
    dest = tmp_path / "bootstrap-static.json"
    dest.write_text('{"elements": [1]}')
    session = FakeSession({})
    payload = fetch.fetch_to_file(session, "/bootstrap-static/", dest)
    assert payload == {"elements": [1]}
    assert session.calls == []


def test_cache_miss_after_ttl(tmp_path):
    dest = tmp_path / "bootstrap-static.json"
    dest.write_text('{"elements": [1]}')
    stale = time.time() - fetch.CACHE_TTL_SECONDS - 60
    os.utime(dest, (stale, stale))
    session = FakeSession({"/bootstrap-static/": FakeResponse(200, '{"elements": [1, 2]}')})
    payload = fetch.fetch_to_file(session, "/bootstrap-static/", dest)
    assert payload == {"elements": [1, 2]}
    assert session.calls == ["/bootstrap-static/"]
    assert json.loads(dest.read_text()) == {"elements": [1, 2]}


def test_force_bypasses_cache(tmp_path):
    dest = tmp_path / "x.json"
    dest.write_text("{}")
    session = FakeSession({"/fixtures/": FakeResponse(200, "[1]")})
    assert fetch.fetch_to_file(session, "/fixtures/", dest, force=True) == [1]
    assert session.calls == ["/fixtures/"]


def test_fetch_all_hits_every_endpoint(tmp_path, cfg):
    ok = lambda body: FakeResponse(200, body)  # noqa: E731
    session = FakeSession({
        "/bootstrap-static/": ok('{"elements": []}'),
        "/fixtures/": ok("[]"),
        "/entry/12345/": ok('{"current_event": 6}'),
        "/entry/12345/history/": ok('{"current": [], "chips": []}'),
        "/entry/12345/event/6/picks/": ok('{"picks": []}'),
        "/leagues-h2h-matches/league/1001/?page=1&entry=12345": ok('{"results": []}'),
        "/leagues-h2h/1001/standings/": ok('{"standings": {"results": []}}'),
        "/leagues-h2h-matches/league/1002/?page=1&entry=12345": ok('{"results": []}'),
        "/leagues-h2h/1002/standings/": ok('{"standings": {"results": []}}'),
    })
    fetch.fetch_all(cfg, tmp_path, session=session)
    assert len(session.calls) == 9
    written = sorted(p.name for p in tmp_path.glob("*.json"))
    assert written == sorted([
        "bootstrap-static.json", "fixtures.json", "entry.json", "entry-history.json",
        "picks.json", "h2h-matches-1001.json", "h2h-standings-1001.json",
        "h2h-matches-1002.json", "h2h-standings-1002.json",
    ])


def test_fetch_all_skips_picks_preseason(tmp_path, cfg, caplog):
    ok = lambda body: FakeResponse(200, body)  # noqa: E731
    cfg = {**cfg, "h2h_league_ids": []}
    session = FakeSession({
        "/bootstrap-static/": ok('{"elements": []}'),
        "/fixtures/": ok("[]"),
        "/entry/12345/": ok('{"current_event": null}'),
        "/entry/12345/history/": ok('{"current": [], "chips": []}'),
    })
    with caplog.at_level(logging.WARNING, logger="fetch"):
        fetch.fetch_all(cfg, tmp_path, session=session)
    assert not (tmp_path / "picks.json").exists()
    assert "skipping picks" in caplog.text


def test_record_count_shapes():
    assert fetch.record_count([1, 2, 3]) == 3
    assert fetch.record_count({"elements": [1, 2]}) == 2
    assert fetch.record_count({"picks": [1]}) == 1
    assert fetch.record_count({"standings": {"results": [1, 2, 3, 4]}}) == 4
    assert fetch.record_count({"a": 1, "b": 2}) == 2


def test_user_agent_is_browser_like():
    session = fetch.make_session()
    assert session.headers["User-Agent"].startswith("Mozilla/5.0")
