---
name: squad-health
trigger: always
chip_independent: false
order: 2
---
## 02 · Squad health

Use the Squad, Flags, Bench strength and Captain candidates tables.

1. **Availability.** List every starter whose status is not `OK`. For each,
   say whether the bench covers them (same position, plays this GW) or a
   transfer is needed.
2. **Transfers.** Recommend at most two moves. State the player out, the
   player in (name a realistic target by price bracket if you cannot see the
   market — the digest does not include non-owned players), and whether a
   points hit is worth it. Default to no hit unless a starter is out for
   several weeks.
3. **Fixtures.** Flag any starter with 5 hard fixtures ahead (FDR 4-5 in
   most of the next-5 columns) as a "plan to move" candidate, not an
   immediate sale.
4. **Captain.** Pick the captain and vice from the candidates table. Prefer
   the highest `ep_next` unless a double gameweek or the overrides say
   otherwise; state the reason in one line.

If module 01 chose Wildcard or Free Hit, replace step 2 with a sketch of the
new XI's shape (formation, budget, three must-keep players) rather than
individual transfers.

Output: one table for availability, one line per transfer, one line for
captain and vice.
