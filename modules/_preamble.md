FPL weekly chip check.
BRIEF_URL=https://raw.githubusercontent.com/mammenk/claudiola/main/brief.md
DECISIONS_URL=https://raw.githubusercontent.com/mammenk/claudiola/main/state/decisions.md

=== STEP 0: GATE — before any other work ===
Fetch BRIEF_URL. Line 1 is an ISO timestamp (UTC). Lines 2-8 are
the header, exactly these keys:
  gameweek, deadline, hours_to_deadline, chips_remaining,
  gameweeks_to_expiry, is_blank, is_double
Read only those for the gate. hours_to_deadline was computed when
the brief was written; compare `deadline` to the current time
yourself for anything time-sensitive.

raw.githubusercontent.com caches ~5 minutes. If I say I have just
re-run the workflow, allow for that lag.

STOP, with one line and nothing further, if:
  A. The deadline is more than 8 days away.
     (International breaks will trigger this — correct, there is
     nothing to decide until squads are back. The workflow's own
     gate uses the same 8 days, so this usually means the brief
     was not regenerated.)
  B. chips_remaining is "none" AND no module below is marked
     CHIP_INDEPENDENT.
  C. The brief is stale: its deadline has passed AND its
     timestamp predates that deadline. The workflow failed to
     regenerate — say so plainly, don't analyse old data.

A gameweek that has just finished is NOT a stop condition. The
days right after a gameweek are the main window for a chip
decision on the next one.

Otherwise print "GATE PASSED —" and the reason, then continue.

Also fetch DECISIONS_URL for what was decided in earlier weeks.
Anything under "## Overrides" in the brief is my instruction and
outranks every module below. Follow it; do not argue with it.

=== STEP 1: MODULES — run in order, skip on false trigger ===
