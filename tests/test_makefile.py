"""The Makefile contract: ci-brief never prints, brief prints only when the gate opens."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

STUB = """#!/bin/sh
# Stand-in for `python3` inside make: skips the network fetch and points
# gate/digest at the fixture with a fixed clock.
case "$2" in
  scripts.fetch)  echo "stub fetch" >&2; exit 0 ;;
  scripts.gate)   exec {py} -m scripts.gate --config {cfg} --data-dir {data} --now "$BRIEF_NOW" ;;
  scripts.digest) exec {py} -m scripts.digest --config {cfg} --data-dir {data} --now "$BRIEF_NOW" --out {out} --overrides {ov} ;;
  *) exec {py} "$@" ;;
esac
"""


@pytest.fixture
def workdir(tmp_path):
    if shutil.which("make") is None:
        pytest.skip("make not installed")
    shutil.copy(ROOT / "Makefile", tmp_path / "Makefile")
    stub = tmp_path / "py"
    stub.write_text(STUB.format(
        py=shutil.which("python3") or "python3",
        cfg=FIXTURES / "config.yaml",
        data=FIXTURES,
        out=tmp_path / "brief.md",
        ov=tmp_path / "overrides.md",
    ))
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return tmp_path


def run_make(workdir: Path, target: str, now: str):
    env = {**os.environ, "BRIEF_NOW": now, "PYTHONPATH": str(ROOT)}
    return subprocess.run(
        ["make", "--no-print-directory", target, f"PY={workdir / 'py'}"],
        cwd=workdir, env=env, capture_output=True, text=True,
    )


def test_ci_brief_writes_but_never_prints(workdir):
    r = run_make(workdir, "ci-brief", "2026-09-25T07:00:00Z")
    assert r.returncode == 0, r.stderr
    assert (workdir / "brief.md").read_text().startswith("2026-09-25T07:00:00Z\n")
    # the gate JSON goes to data/gate.json and the digest to brief.md; stdout has neither
    assert "gameweek: 7" not in r.stdout and "## Squad" not in r.stdout
    assert '"proceed"' not in r.stdout
    assert '"proceed": true' in (workdir / "data" / "gate.json").read_text()
    assert "gate open" in r.stderr


def test_ci_brief_stops_when_gate_closed(workdir):
    r = run_make(workdir, "ci-brief", "2026-09-10T07:00:00Z")
    assert r.returncode == 0, r.stderr
    assert not (workdir / "brief.md").exists()
    assert '"proceed": false' in (workdir / "data" / "gate.json").read_text()
    assert "gate closed" in r.stderr


def test_brief_prints_locally_when_gate_open(workdir):
    r = run_make(workdir, "brief", "2026-09-25T07:00:00Z")
    assert r.returncode == 0, r.stderr
    assert "gameweek: 7" in r.stdout
    assert "## Squad" in r.stdout


def test_brief_stops_cleanly_when_gate_closed(workdir):
    r = run_make(workdir, "brief", "2026-09-10T07:00:00Z")
    assert r.returncode == 0
    assert "## Squad" not in r.stdout
    assert "gate closed" in r.stderr
