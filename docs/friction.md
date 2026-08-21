# Friction log

One line per shortcut or awkwardness, written when it happened. Raw material for "what I'd
do differently."

- 2026-08-21 — Cancellation in `eee` can't persist to Publisher 3's database: the committed
  key is read-only by design, and a persisted cancel would leave the next reviewer's order
  already cancelled. So the cancel is recorded in session state and the request is logged.
  The action is real in the loop and stubbed at the wire — same status as the two publisher
  escalation destinations.
- 2026-08-21 — Added `publishers/*.sql` beside the adapters so the three shapes are readable
  without a Supabase account. Not in the `CLAUDE.md` repo shape; flagged.
