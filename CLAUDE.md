# Weber Impressions — Concierge

A customer support agent for a storefront that sells photobooks from independent publishers.
Built as a take-home for Decagon's Solutions Engineering team. Two SEs will clone this, run
it, read the code, and ask why.

Full reasoning behind every decision here lives in `docs/decisions.md`. This file is the
conclusions.

---

## The thesis

> A support agent's job is to know which truths are its own and which belong to someone
> else — and to route accordingly.

Concierge answers what it can source, names what it can't, acts on what's reversible, and
routes what belongs to a person. Every behavioral choice ladders to that. When something is
ambiguous, resolve it in that direction.

---

## Stack

- **Python** — server, agent loop, tools. Anthropic SDK called directly.
- **HTML / CSS / vanilla JS** — three static screens. No framework.
- **Supabase** — three separate projects, one per publisher, real APIs over the network.
- **Spectral** (SIL OFL), self-hosted in `static/fonts/`.

**No agent framework.** No LangChain, no agent executor, no orchestration library. The
tool-calling loop is the thing being evaluated — it has to be visible in the file.

---

## Repo shape

```
server.py           Serves static files; one /chat endpoint
agent/
  loop.py           The agent loop
  tools.py          Tool definitions and dispatch
  prompts.py        System prompt
  escalation.py     Escalation policy and handoff payload
publishers/
  publisher_1.py    Clean JSON adapter
  publisher_2.py    Spanish JSON adapter, renamed fields
  publisher_3.py    French raw_email adapter — hands the email to the model, no parsing
faqs/               Retrieval corpus, by owner
static/             Three screens, CSS, fonts
docs/
  decisions.md      Full reasoning
  journey.md        The scripted path
README.md
.env.example
```

---

## Architecture

A message travels: **browser → `server.py` → agent loop → tools → Supabase / Anthropic**.

The browser never calls the model. The API key stays server-side.

The loop, each turn: one LLM call with tools and system prompt. Four outcomes — answer from
retrieved FAQs, call a tool, ask a clarifying question, hand off. Only the first two loop.

**Memory is two things.** Session state is the message list passed back each turn. Customer
context (identity, orders) comes from the signed-in portal, already resolved before anyone
types.

---

## The three publishers

Each is a separate Supabase project with its own URL and key. They differ in **integration
maturity**, deliberately — a shared schema with a `publisher` column would make the adapter
layer theater.

| | Shape | Language |
|---|---|---|
| **Publisher 1** | Clean JSON, English status values | English |
| **Publisher 2** | JSON, different field names, Spanish status values, different date format | Spanish |
| **Publisher 3** | One `raw_email` text blob per order — a French confirmation email | French |

`publishers/*.py` normalize all three to one internal shape. Publisher 3 parses a ship date
out of French prose. Call it an **unstructured integration**, never "no API."

**Facts that must hold** (breaking one breaks a journey beat):

- Publisher 1 dispatches same day before 3pm; 5–8 working days to the US
- Publisher 2 dispatches in 1–2 business days; 7–10 to the US
- Publisher 3 publishes **no dispatch time anywhere** — but its confirmation email states
  an estimated arrival directly. The *policy* has a gap; the *order record* doesn't. That
  distinction is the whole point of beats `aaa` and `bbb`, so seed the French email with an
  explicit estimated date.
- Nothing is charged until a book ships, so pre-shipment cancellation is always free

---

## FAQs

**Retrieval: a manifest, not a vector store.** Give the model a manifest of every document —
owner, filename, language, one-line summary — and a tool that returns whole documents. No
embeddings, no chunking, no vector store. Three reasons: 25 small files don't need it;
lexical search breaks exactly where the design lives (an English customer asking about
returns needs Publisher 2's `devoluciones.md`); and it makes the *owner* structure
load-bearing, because the model reasons about who owns the question before it reads
anything. That's the thesis in the retrieval mechanism, and it's defensible out loud.

`faqs/` is organised by owner — `weber-impressions/`, `publisher-1/`, `-2/`, `-3/`. Which
document answers depends on who owns the question.

Each publisher's documents are in that publisher's own language. **Nothing is a translation
of anything else.** Concierge answers in the customer's language regardless of source
language.

**Publisher 3 has no shipping document at all.** That gap is intentional and load-bearing —
it's what journey beat `aaa` runs into. Never add one.

---

## Behavior

**Guardrails, in priority order:**

1. **Never invent information.** No source, no answer. Say what's missing and offer to find
   out.
2. **Never refuse a request for a human.** Honored immediately, no qualifying questions, no
   negotiation.
3. **Never recommend, upsell, or sell.** Recommendations belong to the booksellers. Route
   them.

**Reversibility draws the action line.** The model decides *what to do*; code decides
*what's allowed*.

- **Cancel** an unshipped order autonomously. Nothing has moved, nothing was charged.
- **Never** process a return, refund, or anything post-shipment. Escalate.

Anything expensive or irreversible is gated in code, not left to the model's judgment.

**Off-script input** — unknown orders, nonexistent publishers, out-of-scope questions,
override attempts — declines cleanly and never crashes or improvises. Override attempts get
a light touch, but the decline comes first.

**Voice.** A person at a good shop. Direct, unhurried, never effusive. Says what it knows,
names what it doesn't, doesn't apologize twice. No "Certainly!" No exclamation marks. Never
address the customer by email address — that's a login, not a name.

---

## Escalation

**The escalation design is the thesis in miniature: the model decides when to escalate;
code decides what's forbidden.** Three mechanisms, and only one of them is a rule engine.

**1. Code gates actions, not wording.** Deterministic, checked against order state — never
against the text of a reply:

- Unshipped line → **cancel permitted**, autonomously.
- Shipped, refunded, or anything post-fulfilment → **blocked**, must escalate.

The axis is **reversibility, not value.** A $150 cancel on an unshipped book is reversible
and needs no human. A $5 refund on a shipped one is irreversible and does. Do not gate on
order value or price thresholds — the books are ~$100 each, so a value rule would escalate
the exact cancellation beat `eee` is built to demonstrate.

**2. The model calls an `escalate` tool with a reason.** Frustration, confusion, circling,
a question it can't source — all judgment, all what the model is for. **Do not keyword-match
sentiment or confidence.** No frustration word lists, no scanning replies for "I think" or
"probably." Two reasons: a customer spending $305 on photobooks writes "I've been waiting
three weeks and nobody has replied," not "RIDICULOUS," so the list misses exactly the case
that matters; and inspecting a generated reply for hedging means generating prose in order
to throw it away.

**3. Turn count is a deterministic backstop.** Six customer turns with no tool action and no
handoff → escalate. Cheap, and it catches loops the model doesn't notice it's in.

**Asking for a person is its own path**, not a sentiment signal. Immediate, never
negotiated, no qualifying questions. Explicit in code — it's guardrail 2.

**Destination follows ownership.** A recommendation belongs to Weber Impressions; a
publisher's policy belongs to that publisher. The handoff payload keeps its shape and the
target varies — transcript, summary, detected intent, customer context, `destination`, and a
routing reason.

Weber Impressions routes to a **real Zendesk trial** via API; read the ticket ID off the
response and show it. The two publisher destinations are stubbed and log. One real, two
mocked — stated plainly, not hidden.

**Never commit the Zendesk token.** Supabase URLs and anon keys are publishable by design
and get committed, so the reviewer supplies only `ANTHROPIC_API_KEY`. The Zendesk token
lives in `.env` and most reviewers won't have one — so escalation runs two ways, honestly
labelled:

- *Token present* → real ticket, real ID.
- *Token absent* → say plainly that no Zendesk credentials are configured, and **display the
  payload that would have been sent.**

The fallback is arguably the better reviewer experience: it puts the handoff artifact on
screen instead of hiding it behind a successful API call. Never fall back silently.

---

## The scripted journey

`docs/journey.md` holds the six beats, `aaa` through `fff`. Typing a shortcut in the
Concierge box **populates the input field without sending** — the reviewer reads it and
clicks submit. Runs in order. Free-form input works at any point.

There is no mock mode. The real model is always in the loop — the reviewer supplies their
own Anthropic key and the agent reasons for real at runtime.

**Scripted input, not scripted output.** What's fixed is what the reviewer types. The
reasoning between the guardrails is genuinely probabilistic and replies will differ between
runs. Say so in the README; it's evidence the thing is real, not a defect.

---

## The storefront

**Figma file:** `hKAWVhMcvTZP5vaYKmwtKN`. Call `get_design_context` against these nodes for
exact values and asset URLs — never approximate from description.

| Screen | Node |
|---|---|
| Home | `1:2` |
| Sign in | `7:140` |
| Order + Concierge | `16:249` |

**Three screens, not four.** One order, no order list — fewer clicks for the reviewer.
1440 × 900, desktop only, no breakpoints. Content max-width 1440 with auto margins; rules
run full bleed, content is contained. White background; Concierge pane a barely-warm grey
(`#FAF9F7`) so the split reads without a border.

**Ask for semantic HTML and CSS custom properties** for the type scale and spacing.
Figma-to-code defaults to absolute positioning and magic numbers — that code has to be
readable by a reviewer and by Kiran.

**Red (`#E83826`) marks where to click** — menu, sign in, send. The only color on the site,
so it reads as deliberate wayfinding rather than decoration. Note it in the README.

**The journey hint lives under the input field, in red — never in the conversation.**

> Type `aaa` to begin

After each reply it advances: `Next: bbb`, `Next: ccc`, and so on. **Concierge never mentions
the shortcuts.** A bookseller doesn't know about demo scaffolding, and the escalation payload
carries the transcript — demo instructions inside it would pollute the artifact designed to
look like a real ticket. Off-script input doesn't break it; the hint just keeps showing the
next step.

**Footer stays "A photobook marketplace."** The Bookly rename is explained in the README,
not in the chrome.

**Sign-in doesn't authenticate.** Credentials are pre-filled; submit navigates. Auth is a
documented out-of-scope assumption.

**Welcome message is static.** No API call on page load, no delay before it appears:

> Hello. I have order #94105 in front of me — three books, three publishers. What can I
> help with?

**The loader says what it's doing** — "Searching FAQs…", "Checking Publisher 2…" — not a
generic spinner. Showing the tool calls is the point for this audience.

---

## Order data

Fixed dates, not relative. Consistent with the FAQ dispatch and transit times:

| | Dispatched | Arrives |
|---|---|---|
| Order placed | Mon Aug 17, 2026 | |
| Publisher 1 — William Eggleston — *William Eggleston's Guide* | Mon Aug 17 | Tue Aug 25 |
| Publisher 2 — Joel Meyerowitz, *Cape Light* | Wed Aug 19 | Fri Aug 28 |
| Publisher 3 — Fred Herzog, *Modern Color* | not yet | est. Tue Sep 8 |

Order #94105. Total $305.00 USD. Customer needs the gift by **September 1** — Publishers 1
and 2 make it, Publisher 3 misses, which is why it gets cancelled.

**The order page is text only — no cover thumbnails.** So the three ordered titles need no
image assets, and there's no requirement that they appear in the home grid. A storefront
homepage is a selection, not an order history. `assets/covers/` serves the home grid only.

Don't change any of these without re-checking them against `faqs/`.

**Cover art** is supplied — ten real photobook covers, filenames matching the Figma frame
names (`shore_uncommon_places.jpg`, `webb_the_suffering_of_light.jpg`, and so on). Map them
by name; don't source substitutes.

---

## Build rules

- **Readable over clever.** Few files, no abstractions, traceable top to bottom out loud.
  Every line has to be defensible in an interview.
- **Explain before changing.** If Kiran can't explain a change, it doesn't go in. He directs
  this build and does not write Python.
- **`ANTHROPIC_API_KEY` in `.env` from the first commit.** `.gitignore` it. Commit
  `.env.example`. Server checks at startup and prints one clear line if missing — no
  interactive prompt.
- **No new scope without clearing this test:** does it demonstrate something about the
  thesis that nothing else already demonstrates? If it's a second example of a point already
  made, leave it out.
- **Git from the first minute.** `git init` and commit *before* any code is written.
  `.gitignore` — with `.env` in it — goes in that first commit. **Build private, flip to
  public at submission.** Flipping exposes the entire commit history, not just current
  state — which is good (it shows incremental work) but means anything ever committed stays
  visible even after deletion. Hence `.gitignore` first, not second. Commit as you go.
- **Append to `docs/friction.md`** every time a shortcut is taken or something turns out
  awkward. One line, written then, not reconstructed later. It's the source for the "what
  I'd do differently" slide.
- **Flag contradictions with this file** rather than quietly diverging. If a build decision
  contradicts `CLAUDE.md`, say so — the decision may be right, but the doc gets updated.
- **Nothing exists to prove a point.** If a line, article, or feature is there to
  demonstrate rather than because the business would have it, it reads as staged.
