"""Guard rails for a public repository: nothing local, nothing secret, no printing in CI."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "brief.yml"


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if line]


def test_gitignore_has_the_required_entries():
    lines = {l.strip() for l in (ROOT / ".gitignore").read_text().splitlines()}
    assert {"state/overrides.md", ".env", "data/*.json"} <= lines


def test_overrides_and_data_are_not_tracked():
    names = {p.relative_to(ROOT).as_posix() for p in tracked_files()}
    assert "state/overrides.md" not in names
    assert ".env" not in names
    assert not any(n.startswith("data/") and n.endswith(".json") for n in names)


def test_no_email_addresses_in_tracked_files():
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")
    for path in tracked_files():
        if path.suffix in {".json"}:
            continue  # fixture data; checked for names below instead
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not email.search(text), f"email-like string in {path.relative_to(ROOT)}"


def test_no_email_addresses_in_fixture_json(fixture_dir):
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")
    for path in fixture_dir.glob("*.json"):
        assert not email.search(path.read_text()), path.name


def test_no_token_like_strings_in_tracked_files():
    patterns = [
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"(?i)\b(pl_profile|csrftoken|sessionid)\b\s*[:=]"),
    ]
    for path in tracked_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in patterns:
            assert not pat.search(text), f"{pat.pattern} in {path.relative_to(ROOT)}"


def test_workflow_permissions_are_minimal():
    wf = yaml.safe_load(WORKFLOW.read_text())
    assert wf["permissions"] == {"contents": "read"}
    jobs = wf["jobs"]
    writers = [name for name, job in jobs.items() if (job.get("permissions") or {}).get("contents") == "write"]
    assert writers == ["commit"]
    assert jobs["build"]["permissions"] == {"contents": "read"}


def test_workflow_schedule_and_dispatch():
    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf.get("on") or wf.get(True)  # PyYAML parses a bare `on:` as boolean True
    assert on["schedule"] == [{"cron": "0 7 * * 5"}]
    assert "workflow_dispatch" in on


def test_workflow_actions_pinned_to_sha():
    for line in WORKFLOW.read_text().splitlines():
        if "uses:" in line:
            ref = line.split("uses:")[1].split("#")[0].strip()
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), ref


def test_workflow_never_prints_file_contents():
    text = WORKFLOW.read_text()
    code = re.sub(r"#[^\n]*", "", text)  # drop comments
    for cmd in ("cat ", "tail ", "head ", "less ", "more "):
        assert not re.search(rf"\b{re.escape(cmd)}", code), f"{cmd!r} in workflow"
    assert "overrides" not in code
    # every echo is a fixed status message, never a file's contents
    allowed = ('echo "proceed=', 'echo "Gate closed', 'echo "brief.md unchanged', 'echo "committed brief.md')
    for line in code.splitlines():
        if "echo" in line:
            assert line[line.index("echo"):].startswith(allowed), line


def test_workflow_runs_ci_brief_not_brief():
    wf = yaml.safe_load(WORKFLOW.read_text())
    runs = [s.get("run", "") for s in wf["jobs"]["build"]["steps"]]
    assert any("make ci-brief" in r for r in runs)
    assert not any(re.search(r"make\s+brief\b", r) for r in runs)


def test_workflow_gate_stops_the_commit():
    wf = yaml.safe_load(WORKFLOW.read_text())
    assert wf["jobs"]["commit"]["needs"] == "build"
    assert "proceed == 'true'" in wf["jobs"]["commit"]["if"]
