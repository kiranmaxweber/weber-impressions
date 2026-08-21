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
- 2026-08-21 — First manifest summaries carried the facts ("14 days, unread"), so the model
  answered returns questions without reading the document. Rewrote them as topics only.
  Lesson for the deck: a retrieval index that summarises too well replaces retrieval.
- 2026-08-21 — `agent/order.py` added for the portal's order context (not in the `CLAUDE.md`
  repo shape). The cancel gate keys off it: a charged line has shipped, so it can't be
  cancelled — Weber Impressions' own truth, cross-checked against the publisher's status.
- 2026-08-21 — Beat `aaa` as scripted ("only two have shipping notifications… when can I
  expect them?") reads as a question about this order, and the model correctly checks the
  records instead of answering from policy. Better agent, wrong beat. Proposed: change the
  input, not the prompt.
- 2026-08-21 — The forced backstop call first returned "placeholder" for reason and summary:
  a model made to escalate without being told why fills the form with nothing. Fixed by
  appending a backstop paragraph to the system prompt for that one call. Lesson: a forced
  tool call still needs the model to agree with the premise, or it complies without meaning it.
- 2026-08-21 — Tool events reach the UI with the reply, not live. The server returns JSON
  once; the loader shows a generic line until then. Live needs SSE — deferred, flagged.
