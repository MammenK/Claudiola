from __future__ import annotations

from pathlib import Path

import pytest

from scripts import build_routine

MODULES = Path(__file__).resolve().parent.parent / "modules"
ROUTINE = Path(__file__).resolve().parent.parent / "ROUTINE.md"


def test_seed_modules_parse_in_order():
    mods = build_routine.load_modules(MODULES)
    assert [m["meta"]["name"] for m in mods] == [
        "CHIP DECISION", "SQUAD HEALTH", "H2H CONTEXT", "EXPIRY PRESSURE",
    ]
    assert [m["meta"]["order"] for m in mods] == [1, 2, 3, 4]
    assert all(isinstance(m["meta"]["chip_independent"], bool) for m in mods)


def test_routine_md_is_up_to_date():
    assert ROUTINE.read_text(encoding="utf-8") == build_routine.build_routine(MODULES)


def test_routine_reads_brief_over_raw_github():
    text = ROUTINE.read_text(encoding="utf-8")
    assert "https://raw.githubusercontent.com/mammenk/claudiola/main/brief.md" in text
    # the gate only needs the header keys
    for key in ("hours_to_deadline", "chips_remaining", "gameweeks_to_expiry", "is_blank", "is_double"):
        assert key in text
    assert "M1 CHIP DECISION" in text and "M4 EXPIRY PRESSURE" in text
    assert "STEP 0: GATE" in text and "STEP 2: OUTPUT" in text
    assert "[USER]" not in text and "[ID]" not in text


def test_new_module_slots_in_by_order(tmp_path):
    (tmp_path / "10-late.md").write_text(
        "---\nname: late\ntrigger: always\nchip_independent: true\norder: 10\n---\n## Late\nbody\n"
    )
    (tmp_path / "05-early.md").write_text(
        "---\nname: early\ntrigger: never\nchip_independent: false\norder: 5\n---\n## Early\nbody\n"
    )
    text = build_routine.build_routine(tmp_path)
    assert text.index("M5 early") < text.index("M10 late")
    assert "M5 early — trigger: never." in text
    assert "M10 late — trigger: always. CHIP_INDEPENDENT." in text
    assert "\n   body" in text


def test_missing_frontmatter_key_is_an_error(tmp_path):
    (tmp_path / "01-bad.md").write_text("---\nname: bad\norder: 1\n---\nbody\n")
    with pytest.raises(ValueError, match="missing"):
        build_routine.load_modules(tmp_path)


def test_duplicate_order_is_an_error(tmp_path):
    for n in ("a", "b"):
        (tmp_path / f"01-{n}.md").write_text(
            f"---\nname: {n}\ntrigger: always\nchip_independent: true\norder: 1\n---\nbody\n"
        )
    with pytest.raises(ValueError, match="duplicate"):
        build_routine.load_modules(tmp_path)
