# FAQs

The corpus Concierge retrieves against. Organised by **owner**, not by topic — which
document answers depends on who the question belongs to.

```
weber-impressions/   Storefront policy — ordering, payment, accounts, gifts, tax, privacy
publisher-1/         English. Fast, thorough, same-day dispatch
publisher-2/         Spanish. 1–2 business days, 30-day returns
publisher-3/         French. Deliberately thin
```

## The gap

**Publisher 3 publishes no shipping time.** Not omitted from a file — it has no shipping
document at all. The gap is structural, visible in the file tree, and it's what beat `aaa`
of the journey runs into. Concierge answers for Publishers 1 and 2 and names the absence
for 3 rather than inventing a number.

Publisher 3 is thin in every other respect too: two short documents against six for the
other publishers. That's what a small press with no operations person actually looks like,
and it's the more honest version of a knowledge gap than a single deleted line.

## Three languages, not translations

Each publisher's documents are in that publisher's own language. **Nothing here is a
translation of anything else**, deliberately — near-duplicate documents in a corpus are a
retrieval problem, not a feature, and the agent can end up returning the wrong-language copy
to the wrong reader.

The languages line up with the API shapes: Publisher 2 returns Spanish status values and
writes Spanish policy; Publisher 3 is French and unstructured on both sides. Heterogeneity
is the point.

Concierge answers in the customer's language regardless of the source document's. That's
worth one line on the architecture slide and it's invisible in the journey, which is how it
should be.

## Register

Modelled on how independent photobook publishers actually write — Setanta, FW, RVB, Loose
Joints, Dead Beat Club, GOST, Perimeter, RRB, Chose Commune, Super Labo. Terse, plain, first
person plural, occasionally stern about condition and returns, no marketing padding.

**Nothing here is copied from a real publisher.** Register only.

## Consistency to preserve

- Publisher 1 dispatches same day before 3pm; 5–8 working days to the US
- Publisher 2 dispatches in 1–2 business days; 7–10 to the US
- Publisher 3 states no dispatch time anywhere
- Cancellation before shipment is free everywhere and carries no charge, because nothing is
  charged until a book ships
- Signed and numbered copies are non-returnable except for damage, across all three

Contradicting any of these breaks a beat in the journey.
