"""Assemble ROUTINE.md from modules/.

Every modules/NN-name.md file has YAML frontmatter (name, trigger,
chip_independent, order) followed by the module body. Files starting with an
underscore are fixed parts: _preamble.md goes first, _postamble.md last.
Modules are ordered by their `order` key and rendered as

    M<order> <NAME> — trigger: <trigger>. [CHIP_INDEPENDENT]
       <body, indented>

so ROUTINE.md can be pasted into a routine prompt as-is.
"""
from __future__ import annotations

import argparse
import logging
import textwrap
from pathlib import Path

import yaml

from scripts.common import REPO_ROOT, setup_logging

log = logging.getLogger("build_routine")

MODULES_DIR = REPO_ROOT / "modules"
DEFAULT_OUT = REPO_ROOT / "ROUTINE.md"
REQUIRED_KEYS = ("name", "trigger", "chip_independent", "order")
INDENT = "   "


def parse_module(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: missing YAML frontmatter")
    try:
        _, front, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError(f"{path.name}: unterminated frontmatter") from exc
    meta = yaml.safe_load(front) or {}
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise ValueError(f"{path.name}: frontmatter missing {', '.join(missing)}")
    if not isinstance(meta["chip_independent"], bool):
        raise ValueError(f"{path.name}: chip_independent must be true/false")
    meta["order"] = int(meta["order"])
    meta["trigger"] = str(meta["trigger"]).rstrip(".")
    meta["name"] = str(meta["name"])
    return {"path": path, "meta": meta, "body": body.strip()}


def load_modules(modules_dir: Path = MODULES_DIR) -> list[dict]:
    mods = [parse_module(p) for p in sorted(modules_dir.glob("*.md")) if not p.name.startswith("_")]
    mods.sort(key=lambda m: (m["meta"]["order"], m["path"].name))
    orders = [m["meta"]["order"] for m in mods]
    if len(set(orders)) != len(orders):
        raise ValueError(f"duplicate module order values: {orders}")
    return mods


def module_block(mod: dict) -> str:
    meta = mod["meta"]
    head = f"M{meta['order']} {meta['name']} — trigger: {meta['trigger']}."
    if meta["chip_independent"]:
        head += " CHIP_INDEPENDENT."
    return head + "\n" + textwrap.indent(mod["body"], INDENT)


def build_routine(modules_dir: Path = MODULES_DIR) -> str:
    parts = []
    preamble = modules_dir / "_preamble.md"
    postamble = modules_dir / "_postamble.md"
    if preamble.exists():
        parts.append(preamble.read_text(encoding="utf-8").strip())
    parts.extend(module_block(m) for m in load_modules(modules_dir))
    parts.append(
        "[To add a module: create modules/NN-name.md with frontmatter name,\n"
        " trigger, chip_independent, order; run `make routine`.]"
    )
    if postamble.exists():
        parts.append(postamble.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modules-dir", default=str(MODULES_DIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true", help="exit 1 if the output file is out of date")
    args = parser.parse_args(argv)

    setup_logging()
    text = build_routine(Path(args.modules_dir))
    out = Path(args.out)
    if args.check:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != text:
            log.error("%s is out of date; run `make routine`", out.name)
            return 1
        log.info("%s is up to date", out.name)
        return 0
    out.write_text(text, encoding="utf-8")
    log.info("wrote %s (%d bytes, %d words)", out.name, len(text.encode("utf-8")), len(text.split()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
