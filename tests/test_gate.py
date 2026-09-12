from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from scripts import common, gate


@pytest.fixture
def data(fixture_dir):
    return (
        common.load_json(fixture_dir, common.FILE_BOOTSTRAP),
        common.load_json(fixture_dir, common.FILE_FIXTURES),
        common.load_json(fixture_dir, common.FILE_HISTORY),
    )


def test_proceeds_inside_window(cfg, data, now_near_deadline):
    result = gate.evaluate(cfg, *data, now=now_near_deadline)
    assert result["proceed"] is True
    assert result["gw"] == 7
    assert result["hours_to_deadline"] == 27.0
    assert result["chips_remaining"] == ["freehit", "bboost", "3xc"]
    assert result["is_blank"] is True
    assert result["is_double"] is True
    assert "GW7" in result["reason"]


def test_stops_when_too_far(cfg, data, now_far_from_deadline):
    result = gate.evaluate(cfg, *data, now=now_far_from_deadline)
    assert result["proceed"] is False
    assert "more than 8 days" in result["reason"]


def test_stops_after_deadline(cfg, data):
    after = datetime(2026, 9, 26, 10, 0, 1, tzinfo=timezone.utc)
    result = gate.evaluate(cfg, *data, now=after)
    assert result["proceed"] is False
    assert "already passed" in result["reason"]


def test_window_is_configurable(cfg, data, now_far_from_deadline):
    wide = {**cfg, "max_days_to_deadline": 30}
    assert gate.evaluate(wide, *data, now=now_far_from_deadline)["proceed"] is True


def test_stops_when_no_next_event(cfg, data, now_near_deadline):
    bootstrap, fixtures, history = data
    ended = {**bootstrap, "events": [{**e, "is_next": False} for e in bootstrap["events"]]}
    result = gate.evaluate(cfg, ended, fixtures, history, now=now_near_deadline)
    assert result["proceed"] is False
    assert result["gw"] is None


def test_output_keys_exact(cfg, data, now_near_deadline):
    result = gate.evaluate(cfg, *data, now=now_near_deadline)
    assert set(result) == {
        "proceed", "reason", "gw", "hours_to_deadline", "chips_remaining", "is_blank", "is_double",
    }


def test_cli_prints_json_and_exit_code(fixture_dir, capsys):
    argv = ["--config", str(fixture_dir / "config.yaml"), "--data-dir", str(fixture_dir)]
    assert gate.main(argv + ["--now", "2026-09-25T07:00:00Z"]) == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["proceed"] is True

    assert gate.main(argv + ["--now", "2026-09-10T07:00:00Z"]) == 1
    out = json.loads(capsys.readouterr().out.strip())
    assert out["proceed"] is False
