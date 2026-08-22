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
- 2026-08-21 — Streaming done after all: /chat now returns newline-delimited JSON, one line
  per tool event as it fires, then the result. ~35 lines across server.py and concierge.js.
  Cost is that /chat is no longer "post a list, get a list"; the docstring carries it.
- 2026-08-21 — `git add -A` swept twelve unused font files into a commit and onto GitHub.
  Caught by the clean-checkout test. Untracked and ignored; the lesson is to stage by name
  when the working tree has things that aren't the repo's.
- 2026-08-21 — Zendesk stopped issuing API tokens to new accounts on 28 July 2026, so the
  trial had to use OAuth client credentials. One gotcha: the client must be *Confidential*,
  or the token endpoint returns `unauthorized_client` with no hint that kind is the cause.
  Renewal after trial expiry is three values in `.env`, no code change.
- 2026-08-21 — One journey run stalled at `eee`: at `ddd` the model offered "cancel, or ask
  Publisher 3 to expedite?", so "Yes, do that" was ambiguous and it asked again. Expediting
  isn't an option any publisher publishes. Prompt now says one action, not a menu, and no
  invented options. Scripted input depends on the agent's question having one answer.
- 2026-08-21 — The loop returned only the model's final message, so anything it said before
  a tool call — the booksellers' line at `fff` — reached the ticket transcript but never the
  screen. Found by comparing journey.md to what the reviewer sees. Reply is now every text
  block of the turn.
- 2026-08-21 — Mid-journey probes found two leaks. The publisher stubs returned a string
  where Zendesk returns a number, and the model read it as one: "request #logged to
  publisher-1 (stubbed destination)". Stubs now return no reference. And asked to un-cancel,
  the model said "there's no tool for that" — true, and not the customer's business. Rule
  added: never mention tools or mechanics; say what you can and can't do in their terms.
