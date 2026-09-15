from __future__ import annotations

import re

import pytest

from scripts import digest

HEADER_KEYS = [
    "gameweek", "deadline", "hours_to_deadline", "chips_remaining",
    "gameweeks_to_expiry", "is_blank", "is_double",
]


@pytest.fixture
def brief(cfg, fixture_dir, now_near_deadline, tmp_path):
    return digest.build_brief(cfg, fixture_dir, now_near_deadline, tmp_path / "absent-overrides.md")


def test_first_line_is_iso_timestamp(brief):
    first = brief.splitlines()[0]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", first)
    assert first == "2026-09-25T07:00:00Z"


def test_header_block_follows_timestamp_in_order(brief):
    lines = brief.splitlines()[1:1 + len(HEADER_KEYS)]
    assert [line.split(":")[0] for line in lines] == HEADER_KEYS
    header = dict(line.split(": ", 1) for line in lines)
    assert header["gameweek"] == "7"
    assert header["deadline"] == "2026-09-26T10:00:00Z"
    assert header["hours_to_deadline"] == "27.0"
    assert header["chips_remaining"] == "freehit, bboost, 3xc"
    assert header["gameweeks_to_expiry"] == "12"
    assert header["is_blank"] == "true"
    assert header["is_double"] == "true"
    assert brief.splitlines()[1 + len(HEADER_KEYS)] == ""


def test_under_word_limit(brief):
    assert digest.word_count(brief) < digest.WORD_LIMIT


def test_squad_table_has_15_players_with_flags_and_fdr(brief):
    squad = brief.split("## Squad")[1].split("## Flags")[0]
    rows = [l for l in squad.splitlines() if re.match(r"\| \d+ \|", l)]
    assert len(rows) == 15
    assert "Haaland (C)" in squad and "Salah (V)" in squad
    assert "INJ 0%" in squad and "DOUBT 75%" in squad
    # next-5 FDR columns, a double and a home/away marker
    assert "| GW7 | GW8 | GW9 | GW10 | GW11 |" in squad
    assert "CHE(H)3 + MCI(A)3" in squad


def test_bench_captains_chips_h2h_sections(brief):
    assert "## Bench strength" in brief
    assert "| XI ep_next | Bench ep_next | Bench / XI |" in brief
    captains = brief.split("## Captain candidates")[1].split("## Chips")[0]
    names = re.findall(r"^\| ([A-Za-z]+)", captains, flags=re.M)
    assert names == ["Player", "Haaland", "Salah", "Palmer"]
    assert "| Wildcard | used GW3 | not yet |" in brief
    assert "| Free Hit | available | not yet |" in brief
    h2h = brief.split("## H2H")[1].split("## Overrides")[0]
    assert "| Office H2H | 2 | 15 | Tiki Taka | 5 | 6 | 9 | 291 |" in h2h
    assert "| Old Boys H2H | 5 | 6 | Long Ball FC | 4 | 9 | -3 | 301 |" in h2h


def test_no_manager_personal_names_in_brief(brief):
    # H2H opponents are shown by team name only.
    assert "Second Manager" not in brief and "Fifth Manager" not in brief


def test_overrides_absent_is_handled(brief):
    assert "_none (state/overrides.md not present)_" in brief


def test_overrides_appended_verbatim(cfg, fixture_dir, now_near_deadline, tmp_path):
    ov = tmp_path / "overrides.md"
    ov.write_text("## Overrides\n- Hold Bench Boost for GW9.\n- Never bench Salah.\n")
    text = digest.build_brief(cfg, fixture_dir, now_near_deadline, ov)
    assert text.rstrip().endswith("- Hold Bench Boost for GW9.\n- Never bench Salah.")
    assert "not present" not in text


def test_cli_writes_file_and_prints_nothing(fixture_dir, tmp_path, capsys):
    out = tmp_path / "brief.md"
    rc = digest.main([
        "--config", str(fixture_dir / "config.yaml"),
        "--data-dir", str(fixture_dir),
        "--now", "2026-09-25T07:00:00Z",
        "--out", str(out),
        "--overrides", str(tmp_path / "none.md"),
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert out.exists()
    assert out.read_text().startswith("2026-09-25T07:00:00Z\ngameweek: 7\n")


def test_secret_in_overrides_never_reaches_stdout_or_log(fixture_dir, tmp_path, capsys, caplog):
    ov = tmp_path / "overrides.md"
    ov.write_text("SECRET-OVERRIDE-TEXT\n")
    digest.main([
        "--config", str(fixture_dir / "config.yaml"),
        "--data-dir", str(fixture_dir),
        "--now", "2026-09-25T07:00:00Z",
        "--out", str(tmp_path / "brief.md"),
        "--overrides", str(ov),
    ])
    captured = capsys.readouterr()
    assert "SECRET-OVERRIDE-TEXT" not in captured.out
    assert "SECRET-OVERRIDE-TEXT" not in captured.err
    assert "SECRET-OVERRIDE-TEXT" not in caplog.text


def test_missing_picks_is_handled(cfg, fixture_dir, now_near_deadline, tmp_path):
    import shutil

    data = tmp_path / "data"
    shutil.copytree(fixture_dir, data)
    (data / "picks.json").unlink()
    text = digest.build_brief(cfg, data, now_near_deadline, None)
    assert "no picks available yet" in text
    assert text.startswith("2026-09-25T07:00:00Z\ngameweek: 7\n")


def test_h2h_leagues_discovered_when_config_empty(cfg, fixture_dir, now_near_deadline):
    text = digest.build_brief({**cfg, "h2h_league_ids": []}, fixture_dir, now_near_deadline, None)
    assert "| Office H2H |" in text and "| Old Boys H2H |" in text


def test_h2h_leagues_restricted_by_config(cfg, fixture_dir, now_near_deadline):
    text = digest.build_brief({**cfg, "h2h_league_ids": [1002]}, fixture_dir, now_near_deadline, None)
    assert "| Office H2H |" not in text and "| Old Boys H2H |" in text


def test_h2h_unexpected_standings_shape_degrades_not_crashes(cfg, fixture_dir, now_near_deadline, tmp_path):
    import json
    import shutil

    data = tmp_path / "data"
    shutil.copytree(fixture_dir, data)
    path = data / "h2h-standings-1001.json"
    standings = json.loads(path.read_text())
    for row in standings["standings"]["results"]:
        row.pop("total", None)
        row.pop("points_for", None)
    path.write_text(json.dumps(standings))
    text = digest.build_brief({**cfg, "h2h_league_ids": [1001]}, data, now_near_deadline, None)
    assert "| Office H2H | 2 | - | Tiki Taka | 5 | - | - | - |" in text


def test_captain_candidates_exclude_goalkeepers(cfg, fixture_dir, now_near_deadline, tmp_path):
    import json
    import shutil

    data = tmp_path / "data"
    shutil.copytree(fixture_dir, data)
    path = data / "bootstrap-static.json"
    bootstrap = json.loads(path.read_text())
    for el in bootstrap["elements"]:
        if el["web_name"] == "Raya":
            el["ep_next"] = "99.0"
    path.write_text(json.dumps(bootstrap))
    text = digest.build_brief(cfg, data, now_near_deadline, None)
    captains = text.split("## Captain candidates")[1].split("## Chips")[0]
    assert "Raya" not in captains
    assert "Haaland" in captains
