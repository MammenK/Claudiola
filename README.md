# Claudiola

A weekly Fantasy Premier League brief.

- **Python scripts** fetch the public FPL API and compute a digest.
- **GitHub Actions** runs them every Friday and commits `brief.md` to `main`.
- **A Claude routine** (`ROUTINE.md`) reads `brief.md` over
  `raw.githubusercontent.com` and does the judgement: chip, transfers,
  captain, H2H context.

The scripts fetch and tabulate. They never analyse. All judgement lives in
the routine, and the manager can steer it with a local, never-committed
`state/overrides.md`.

## Before the first push — repository settings

This repository is public. Apply these in GitHub before pushing anything:

1. **Settings › Code security › Secret scanning**: enable *Secret scanning*
   **and** *Push protection*.
2. **Settings › Rules › Rulesets**, new branch ruleset targeting `main`:
   - *Block force pushes*: on
   - *Restrict deletions*: on
   - *Require a pull request before merging*: **off** — the Actions
     workflow commits `brief.md` directly to `main`.
   - No bypass list is needed; the workflow only does ordinary pushes.

The workflow needs nothing else: no secrets, no tokens, no FPL login. Every
endpoint it uses is public.

## Layout

| Path | What |
|---|---|
| `config.yaml` | `team_id`, `h2h_league_ids`, `half_deadline_gw`, `max_days_to_deadline` |
| `scripts/fetch.py` | Public FPL API → `data/*.json`, 6 h local cache, browser User-Agent, fails loudly with the status code |
| `scripts/gate.py` | Prints `{proceed, reason, gw, hours_to_deadline, chips_remaining, is_blank, is_double}`; exit 1 when `proceed` is false |
| `scripts/digest.py` | Writes `brief.md` at the repo root; never prints it |
| `scripts/build_routine.py` | Assembles `ROUTINE.md` from `modules/` |
| `scripts/common.py` | Shared helpers (chips, halves, blank/double detection) |
| `modules/` | One markdown file per analysis module, YAML frontmatter |
| `ROUTINE.md` | Generated. The routine prompt. Do not edit by hand |
| `state/decisions.md` | Append-only log: date, GW, verdict, reason |
| `state/overrides.md` | Local only, gitignored. See below |
| `brief.md` | Generated weekly by Actions (or `make brief` locally) |
| `tests/` | pytest, offline, against `tests/fixtures/*.json` |
| `.github/workflows/brief.yml` | Friday 07:00 UTC cron + manual dispatch |

## Local use

Python 3.11. Dependencies are `requests` and `pyyaml` only.

```
python -m pip install -r requirements-dev.txt
```

Set `team_id` in `config.yaml`. H2H leagues are discovered from the entry
automatically; list `h2h_league_ids` only to restrict to some of them. Then:

```
make brief      # fetch → gate → digest → print brief.md
make ci-brief   # the same without the print; what the Actions job runs
make fetch      # just refresh data/ (cached 6 h; `make fetch-force` to bypass)
make gate       # print the gate JSON
make digest     # write brief.md from data/
make routine    # regenerate ROUTINE.md from modules/
make test       # pytest, fully offline
```

The pipeline is defined once, in `ci-brief`; `brief` just adds the print.
`ci-brief` writes the gate's JSON to `data/gate.json` (gitignored) and, when
the gate is closed (deadline more than `max_days_to_deadline` away, or
already passed), stops there with exit 0 and leaves `brief.md` untouched.
So `make brief` prints nothing that week, and the workflow reads
`data/gate.json` to decide whether there is anything to commit.

Every script accepts `--data-dir`, `--config` and `--now <ISO>` so you can
run against the fixture: 

```
python -m scripts.gate --config tests/fixtures/config.yaml --data-dir tests/fixtures --now 2026-09-25T07:00:00Z
```

### Running it from GitHub instead

You don't need Python locally. Actions › **brief** › *Run workflow*, pick
the branch, and tick **skip_gate** if the next deadline is more than
`max_days_to_deadline` away (otherwise the gate closes and nothing is
written). The run commits `brief.md` to the branch you picked; open the
file on GitHub to read it. The log shows only status lines.

The Friday schedule runs on `main` with the gate in force.

### `brief.md` format

The first line is an ISO timestamp. Then a `key: value` header block:

```
gameweek, deadline, hours_to_deadline, chips_remaining,
gameweeks_to_expiry, is_blank, is_double
```

The routine reads only that header at its own gate, so it stays at the very
top. After it: tables for the squad (position, price, status flag, next-5
FDR), flags, bench strength, top-3 captain candidates, chips used and
remaining, H2H opponents with rank and points gap, then overrides. Under
800 words, tables not prose, no analysis.

`gameweeks_to_expiry` counts the gameweeks left *after* the current one
before this half's chips expire; `0` means this is the last chance.

## Filling `state/overrides.md` (local only)

`state/overrides.md` is gitignored and must stay that way. It is where you
tell the routine things the API cannot: a chip you are saving, a player you
refuse to sell, a captain preference, a rumour you trust.

```
cp state/overrides.example.md state/overrides.md
$EDITOR state/overrides.md
make brief
```

`digest.py` appends the file **verbatim** to the end of `brief.md` when it
exists. In CI it does not exist, so the committed `brief.md` never contains
it. The routine treats the `## Overrides` section as the manager's word and
follows it over its own defaults.

Since the committed brief never carries overrides, the routine only sees
them if you paste the local `brief.md` into the conversation yourself, or
run the routine against a local copy. That is deliberate: overrides are the
one place your private reasoning lives, and it is never pushed.

## Why nothing may be printed in CI

The repository is public, so **every Actions log is public**. Anyone can
read every run. Therefore:

- `fetch.py` logs status codes, byte counts and record counts. Never a
  response body.
- `digest.py` **writes** `brief.md`. It never prints it. If it did, and you
  ever ran the workflow with an overrides file present, your private notes
  would sit in a public log forever.
- No workflow step may `cat`, `tail`, `head` or `echo` the contents of
  `brief.md`, `data/*.json` or `state/overrides.md`.
- `make brief` prints locally because your terminal is yours. The CI job
  runs `make ci-brief` instead: the same fetch → gate → digest, minus the
  print. A test fails if the workflow ever calls `make brief`.

`tests/test_hygiene.py` enforces the mechanical parts: the gitignore
entries, no email-like or token-like strings in tracked files, workflow
permissions, SHA-pinned actions and no printing commands in the workflow.

## Adding a module

1. Create `modules/NN-name.md` with this frontmatter:

   ```
   ---
   name: name
   trigger: always            # or a condition on the brief header, in words
   chip_independent: true     # false if it should assume module 01's chip verdict
   order: 5                   # unique; modules run in ascending order
   ---
   ## NN · Title

   What the routine should look at, in what order, and what to output.
   ```

2. Keep the body to what the routine should *decide* and *output*. The
   digest supplies data; the module supplies the questions.
3. Run `make routine` and commit both the module and the regenerated
   `ROUTINE.md`. The tests fail if `ROUTINE.md` is stale.

Files in `modules/` that start with `_` are fixed parts of the routine
(`_preamble.md`, `_postamble.md`), not modules.

## The routine

`ROUTINE.md` is the prompt. Point a Claude routine at it (or paste it). It
fetches `brief.md` and `state/decisions.md` from
`https://raw.githubusercontent.com/mammenk/claudiola/main/`, checks the
header, runs the modules in order, and ends with a verdict table plus one
line to append to `state/decisions.md`.

## How the weekly run works

1. Friday 07:00 UTC (or manual dispatch), job `build`, `contents: read`:
   `make ci-brief` (fetch → gate → digest). If the gate is closed, the run
   ends there with no commit and no failure.
2. Job `commit`, `contents: write`: downloads `brief.md` from the build job
   and commits it to the branch the run started from (`main` on schedule)
   only if it changed. The commit identity is GitHub's public Actions bot
   account.

Set `max_days_to_deadline` so the Friday run lands inside the window for a
normal Saturday deadline; 8 days also covers midweek and shifted rounds.
