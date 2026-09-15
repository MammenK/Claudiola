from scripts import common


def test_chips_remaining_respects_halves():
    history = {"chips": [{"name": "wildcard", "event": 3}, {"name": "bboost", "event": 25}]}
    assert common.chips_remaining(history, gw=7, half_deadline_gw=19) == ["freehit", "bboost", "3xc"]
    assert common.chips_remaining(history, gw=26, half_deadline_gw=19) == ["wildcard", "freehit", "3xc"]


def test_chips_remaining_all_used():
    history = {"chips": [{"name": c, "event": 2 + i} for i, c in enumerate(common.CHIPS)]}
    assert common.chips_remaining(history, gw=10, half_deadline_gw=19) == []


def test_gameweeks_to_expiry():
    assert common.gameweeks_to_expiry(7, 19, 38) == 12
    assert common.gameweeks_to_expiry(19, 19, 38) == 0
    assert common.gameweeks_to_expiry(20, 19, 38) == 18
    assert common.gameweeks_to_expiry(38, 19, 38) == 0


def test_parse_iso_handles_z_suffix():
    dt = common.parse_iso("2026-09-26T10:00:00Z")
    assert dt.tzinfo is not None
    assert common.iso_z(dt) == "2026-09-26T10:00:00Z"


def test_blank_double_flags(fixture_dir):
    bootstrap = common.load_json(fixture_dir, common.FILE_BOOTSTRAP)
    fixtures = common.load_json(fixture_dir, common.FILE_FIXTURES)
    assert common.blank_double_flags(bootstrap, fixtures, 7) == (True, True)
    assert common.blank_double_flags(bootstrap, fixtures, 8) == (False, False)


def test_load_config_requires_team_id(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("team_id: 0\n")
    import pytest

    with pytest.raises(SystemExit):
        common.load_config(path)


def test_h2h_league_ids_discovered_from_entry(fixture_dir):
    entry = common.load_json(fixture_dir, common.FILE_ENTRY)
    assert common.h2h_league_ids({"h2h_league_ids": []}, entry) == [1001, 1002]
    assert common.h2h_league_ids({}, entry) == [1001, 1002]
    assert common.h2h_league_ids({"h2h_league_ids": [1002]}, entry) == [1002]
    assert common.h2h_league_ids({}, {"leagues": {"h2h": []}}) == []
