---
name: chip-decision
trigger: always
chip_independent: true
order: 1
---
## 01 · Chip decision

Decide whether to play a chip this gameweek. Use the header's
`chips_remaining`, `is_blank`, `is_double` and `gameweeks_to_expiry`, plus
the Chips, Squad and Bench strength tables.

Consider, in this order:

1. **Overrides.** If the manager has ruled a chip in or out, that stands.
2. **Blank / double gameweek.** A double favours Bench Boost (if the bench
   is strong and all play twice) and Triple Captain (on a player with two
   fixtures). A blank with several of the XI missing favours Free Hit.
3. **Squad health.** Three or more flagged starters with no like-for-like
   bench cover is a Wildcard or Free Hit signal, not a transfer-hit signal.
4. **Expiry.** See module 04; an unused chip close to expiry lowers the bar
   for playing it, but never to zero — a wasted chip is still a wasted chip.

Output a table:

| Chip | Verdict | Reason |
|---|---|---|

with one row per chip in `chips_remaining` and a verdict of `play`, `hold`
or `consider next GW`. Exactly one chip can be played per gameweek; if two
look attractive, pick one and say why.
