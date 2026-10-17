from scripts import pool


def test_pool_rows_from_fixture(fixture_dir, tmp_path):
    out = pool.write_pool(fixture_dir, tmp_path / "pool.csv")
    text = out.read_text().splitlines()
    assert text[0].split(",")[:5] == ["id", "web_name", "team", "pos", "price"]
    assert len(text) == 1 + 20  # header + fixture players
    assert any(line.startswith("13,Haaland,MCI,FWD,14.2,") for line in text)


def test_pool_cli_prints_nothing(fixture_dir, tmp_path, capsys):
    assert pool.main(["--data-dir", str(fixture_dir), "--out", str(tmp_path / "p.csv")]) == 0
    assert capsys.readouterr().out == ""
