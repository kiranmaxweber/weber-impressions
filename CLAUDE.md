# Weber Impressions — Concierge

A customer support agent for a storefront that sells photobooks from independent publishers.
Built as a take-home for Decagon's Solutions Engineering team. Two SEs will clone this, run
it, read the code, and ask why.

The full reasoning behind every decision — and the friction log — is kept with Kiran's notes,
outside the repo. This file is the conclusions, and it describes what is built.

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
server.py           Serves static files; one endpoint, POST /chat, which streams
agent/
  loop.py           The agent loop, and the turn-count backstop
  tools.py          Tool definitions, dispatch, and the cancel gate
  prompts.py        System prompt, FAQ manifest, the register
  escalation.py     Handoff payload, destination by ownership, Zendesk
  order.py          The order as the portal knows it: lines, prices, what's been charged
publishers/
  publisher_1.py    Clean JSON adapter
  publisher_2.py    Spanish JSON adapter, renamed fields, dd/mm/yyyy
  publisher_3.py    French raw_email adapter — hands the email to the model, no parsing
  publisher_N.sql   The migration that built each table, readable without Supabase
faqs/               Retrieval corpus, by owner
static/             Three screens, style.css, concierge.js, covers, fonts
README.md           Run it, the scripted path, what's in the box
.env.example
```

---

## Architecture

A message travels: **browser → `server.py` → agent loop → tools → Supabase / Anthropic**.

The browser never calls the model. The API key stays server-side.

The loop, each turn: one LLM call with tools and system prompt. Four outcomes — answer from
retrieved FAQs, call a tool, ask a clarifying question, hand off. Only the tool call loops.
The reply is everything the model says in the turn, before and after tool calls. Tool
events stream to the browser as they fire.

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

`publishers/*.py` normalize the first two to one internal shape. Publisher 3's adapter
returns the email and the model reads the date out of it — no regex, no date parsing in
code. Call it an **unstructured integration**, never "no API."

The publishable keys are committed: every table has RLS on with a single public `select`
policy, so the keys can only read.

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
owner, filename, language, and its *topic* — and a tool that returns whole documents. The
manifest names what a document is about, never what it says; the first draft carried the
facts and the model answered from the index without reading. No
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

**One action, not a menu.** When a fix is offered, offer one, so "yes" means one thing. No
options the policy doesn't provide (rush shipping, asking a publisher to expedite). Never
mention tools or mechanics; say what it can and can't do in the customer's terms.

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
order value or price thresholds — the books are ~$100 each, and a value rule would put a
human in front of the one action that needs none, which is also why the journey's
cancellation completes without one.

**2. The model calls an `escalate` tool with a reason.** Frustration, confusion, circling,
a question it can't source — all judgment, all what the model is for. **Do not keyword-match
sentiment or confidence.** No frustration word lists, no scanning replies for "I think" or
"probably." Two reasons: a customer spending $305 on photobooks writes "I've been waiting
three weeks and nobody has replied," not "RIDICULOUS," so the list misses exactly the case
that matters; and inspecting a generated reply for hedging means generating prose in order
to throw it away.

**3. Turn count is a deterministic backstop.** Six customer turns with no tool call of any
kind → the loop forces one `escalate` call, so code decides *that* it's time and the model
writes the summary. The payload records `trigger: turn_limit`; a forced handoff is never
indistinguishable from a chosen one.

**Asking for a person is its own path**, not a sentiment signal. Immediate, never
negotiated, no qualifying questions. Explicit in code — it's guardrail 2.

**Destination follows ownership.** A recommendation belongs to Weber Impressions; a
publisher's policy belongs to that publisher. The handoff payload keeps its shape and the
target varies — transcript (from the greeting on), summary, intent, customer context, the
order's lines with their status, `destination`, a routing reason, and `trigger`.

Weber Impressions routes to a **real Zendesk trial**; the ticket ID comes off the response
and into the reply. The two publisher destinations are stubbed and log, and return no
reference number — the agent says the request is with Publisher N and stops. One real, two
mocked — stated plainly, not hidden.

**The ticket.** Subject "Escalation from Concierge: <intent>". Body: the customer's email
leading the summary; why it's here; the order on one line (number, date, total) with its
lines and their status; the whole conversation as Customer/Concierge bullets. Requester is
the customer's profile; the order number goes in a custom field. No `#` before a number
anywhere in ticket text — Zendesk links it as a ticket.

**Zendesk authenticates with OAuth client credentials** — Zendesk stopped issuing API tokens
to new accounts in July 2026. Three values in `.env`: subdomain, client id, client secret;
the OAuth client must be *Confidential*. A new trial means three new values and no code
change. Never commit them. Supabase keys are publishable by design and get committed, so a
reviewer supplies only `ANTHROPIC_API_KEY` — so escalation runs two ways, honestly labelled:

- *Credentials present* → real ticket, real ID.
- *Credentials absent* → say plainly that no help desk is connected, and the interface
  **displays the payload that would have been sent.**

The fallback is arguably the better reviewer experience: it puts the handoff artifact on
screen instead of hiding it behind a successful API call. Never fall back silently.

---

## The scripted journey

Six beats, `aaa` through `fff`; the inputs live in `static/concierge.js` and the README
carries the script with what to notice at each. Typing a shortcut in the Concierge box
**populates the input field without sending** — the reviewer reads it and clicks submit.
Runs in order. Free-form input works at any point.

| | Input | What it shows |
|---|---|---|
| `aaa` | How long does shipping usually take from your publishers? | Policy from three documents in three languages; Publisher 3's gap named |
| `bbb` | Where do mine actually stand? | Three live lookups, three shapes |
| `ccc` | One of those won't arrive in time. | Which one, and by when — asked once |
| `ddd` | The third. I need it by September 1. | Cancel offered, not a return |
| `eee` | Yes, do that. | The autonomous action, gated in code |
| `fff` | Any recommendations? | Booksellers' work; a real request opened |

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
| Order \| Concierge | `53:323` ("page 2" — the one that's built) |

**Three screens, not four.** One order, no order list — fewer clicks for the reviewer.
1440 wide, desktop only, no breakpoints. Content max-width 1440 with auto margins; rules
run full bleed, content is contained. **Height follows the window**, not the comp's 900: a
14" MacBook browser is nearer 850, so nothing is pinned and the conversation pane takes the
slack. White throughout; the two columns are split by a 1px vertical rule at x=525.

**Ask for semantic HTML and CSS custom properties** for the type scale and spacing.
Figma-to-code defaults to absolute positioning and magic numbers — that code has to be
readable by a reviewer.

**Red (`#E83826`) marks where to click** — the menu icon on Home, the Sign in button, the
send arrow. The only color on the site, so it reads as deliberate wayfinding rather than
decoration. On Sign in and Order the menu icon is black: there it's a way back, not the
next step. Note the red in the README.

**The journey hint lives inside the chat box — never in the conversation.** Black text, the
shortcut as a red chip:

> Type `aaa` to begin

After each reply it advances — `Type bbb to continue` … `Type fff to finish` — hiding while
the box has focus or text. **Concierge never mentions the shortcuts.** A bookseller doesn't
know about demo scaffolding, and the escalation payload carries the transcript — demo
instructions inside it would pollute the artifact designed to look like a real ticket.
Off-script input mid-way doesn't break it; the hint keeps showing the next step. Off-script
input at the last step ends the hints — the reviewer finished their own way.

**Footer stays "A photobook marketplace."** The Bookly rename is explained in the README,
not in the chrome.

**Sign-in doesn't authenticate.** Credentials are pre-filled; submit navigates. "Forgot
password?" shows a one-line "reset link sent" note, matching what the FAQ promises. Auth is
a documented out-of-scope assumption.

**Welcome message is static.** No API call on page load, no delay before it appears, the
order number bold to tie the conversation to the order on the left:

> Hello. I have order **#94105** in front of me — three books, three publishers. What can I
> help with?

**The loader says what it's doing** — "Reading publisher-2/envios.md…", "Checking Publisher
3…" — streamed as each tool fires, in red, one per line; once the reply lands they collapse
to a single small line. Showing the tool calls is the point for this audience.

**Replies render paragraphs, `- ` lists, and `**bold**`** — the only structure the model is
asked to produce. Lines of the order are always **Publisher N (Title)**, in order; the
storefront's name is always bold; nothing else is.

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

Prices: $120, $100, $85. The customer is photobookcollector@icloud.com — the Zendesk
requester, never how Concierge addresses them. Order headings: Placed, Titles, Total.

**The order page is text only — no cover thumbnails.** So the three ordered titles need no
image assets, and there's no requirement that they appear in the home grid. A storefront
homepage is a selection, not an order history. `static/covers/` serves the home grid only.

Don't change any of these without re-checking them against `faqs/`.

**Cover art** is supplied — ten real photobook covers, filenames matching the Figma frame
names (`shore_uncommon_places.jpg`, `webb_the_suffering_of_light.jpg`, and so on). Map them
by name; don't source substitutes.

---

## Build rules

- **Readable over clever.** Few files, no abstractions, traceable top to bottom out loud.
  Every line has to be defensible in an interview.
- **Explain before changing.** If Kiran can't explain a change, it doesn't go in.
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
  visible even after deletion. Hence `.gitignore` first, not second. Commit as you go, and
  stage by name — `git add -A` once swept twelve unused font files onto GitHub.
- **Append to the friction log** (kept with the decisions, outside the repo) every time a
  shortcut is taken or something turns out awkward. One line, written then, not
  reconstructed later. It's the source for the "what I'd do differently" slide.
- **Flag contradictions with this file** rather than quietly diverging. If a build decision
  contradicts `CLAUDE.md`, say so — the decision may be right, but the doc gets updated.
- **Nothing exists to prove a point.** If a line, article, or feature is there to
  demonstrate rather than because the business would have it, it reads as staged.
