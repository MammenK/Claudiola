---
name: expiry-pressure
trigger: gameweeks_to_expiry <= 4 and chips_remaining is not empty
chip_independent: true
order: 4
---
## 04 · Expiry pressure

Chips expire at the end of the half (`gameweeks_to_expiry` counts the
gameweeks left after this one; `0` means this is the last chance).

For each chip in `chips_remaining`:

1. State the number of remaining opportunities, including this gameweek.
2. Give a one-line plan: play now, play in a specific later gameweek (name
   it and why — a known double, a fixture swing), or accept losing it.
3. If two or more chips remain with fewer gameweeks than chips, say which
   one to sacrifice. Only one chip per gameweek is allowed.

Output a table:

| Chip | GWs left | Plan |
|---|---|---|
