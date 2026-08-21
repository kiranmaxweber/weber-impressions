"""Handoff to a person. The payload keeps its shape; the destination varies by who owns the issue.

Weber Impressions goes to a real Zendesk trial when credentials are configured. The three
publisher destinations are stubs that log. One real, two mocked — and when no Zendesk token
is present, the Weber Impressions handoff is returned undelivered with the payload shown,
never silently dropped.
"""

import html
import json
import os
import re

import requests

from agent.order import ORDER


def cancelled_lines(messages):
    """The transcript is the record. A cancel_line call that succeeded means the line is cancelled."""
    succeeded = set()
    for m in messages:
        if m["role"] == "user" and isinstance(m["content"], list):
            for b in m["content"]:
                if b.get("type") == "tool_result" and not b.get("is_error"):
                    succeeded.add(b["tool_use_id"])
    cancelled = set()
    for m in messages:
        if m["role"] == "assistant" and isinstance(m["content"], list):
            for b in m["content"]:
                if b.get("type") == "tool_use" and b["name"] == "cancel_line" and b["id"] in succeeded:
                    cancelled.add(int(b["input"]["publisher"]))
    return cancelled


# The static greeting on the order page. Not in the message list, so it's added to the
# transcript here. Keep in step with static/order.html.
WELCOME = "Hello. I have order #94105 in front of me — three books, three publishers. What can I help with?"
ORDER_NUMBER_FIELD = 52777396366100  # Zendesk custom ticket field: order number


def transcript(messages):
    """Plain turns only, from the greeting on. Tool calls and results stay out of the ticket."""
    turns = [{"role": "assistant", "text": WELCOME}]
    for m in messages:
        if isinstance(m["content"], str):
            turns.append({"role": m["role"], "text": m["content"]})
            continue
        text = "".join(b.get("text", "") for b in m["content"] if b.get("type") == "text")
        if text:
            turns.append({"role": m["role"], "text": text})
    return turns


def stalled(messages, limit=6):
    """The deterministic backstop: six customer turns with no tool call of any kind — no
    lookup, no cancel, no handoff. Checked against the message list, never the reply text."""
    customer_turns = [i for i, m in enumerate(messages) if m["role"] == "user" and isinstance(m["content"], str)]
    if len(customer_turns) < limit:
        return False
    since = customer_turns[-limit]
    for m in messages[since:]:
        if m["role"] == "assistant" and any(b.get("type") == "tool_use" for b in m["content"]):
            return False
    return True


def line_status(line, messages):
    if line["publisher"] in cancelled_lines(messages):
        return "cancelled in this conversation"
    return "shipped" if line["charged"] else "not shipped"


def handoff(destination, intent, reason, summary, messages, trigger="model"):
    """trigger is "model" when the model chose to escalate, "turn_limit" when code forced it.
    A forced handoff must be distinguishable from a chosen one in the ticket."""
    payload = {
        "destination": destination,
        "trigger": trigger,
        "routing_reason": reason,
        "intent": intent,
        "summary": summary,
        "customer": {"email": ORDER["customer_email"], "order": ORDER["number"], "order_total_usd": ORDER["total_usd"]},
        "lines": [{"publisher": l["publisher"], "title": l["title"], "status": line_status(l, messages)} for l in ORDER["lines"]],
        "transcript": transcript(messages),
    }

    if destination == "weber-impressions":
        return zendesk(payload)

    # Publisher help desks — stubbed. Logged so the shape is visible in the server output.
    print(f"[handoff → {destination}] (stub)\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    payload["delivered"] = True
    payload["reference"] = f"logged to {destination} (stubbed destination)"
    return payload


def zendesk(payload):
    """Weber Impressions' help desk. OAuth client credentials: exchange the client id and
    secret for a short-lived bearer token, then create the ticket. Zendesk stopped issuing
    API tokens to new accounts in July 2026, so this is the only route for a trial. Renewing
    an expired trial means three new values in .env and no code change."""
    subdomain = os.environ.get("ZENDESK_SUBDOMAIN")
    client_id = os.environ.get("ZENDESK_CLIENT_ID")
    client_secret = os.environ.get("ZENDESK_CLIENT_SECRET")
    if not (subdomain and client_id and client_secret):
        payload["delivered"] = False
        payload["reference"] = None
        payload["note"] = "No Zendesk credentials configured. The interface shows the customer this payload; tell them the request couldn't be filed."
        print(f"[handoff → weber-impressions] NOT DELIVERED\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
        return payload

    base = f"https://{subdomain}.zendesk.com"
    token = requests.post(
        f"{base}/oauth/tokens",
        data={"grant_type": "client_credentials", "client_id": client_id,
              "client_secret": client_secret, "scope": "tickets:write"},
        timeout=15,
    )
    token.raise_for_status()
    access_token = token.json()["access_token"]

    r = requests.post(
        f"{base}/api/v2/tickets.json",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"ticket": {
            "subject": f"Escalation from Concierge: {payload['intent']}",
            "comment": {"html_body": ticket_html(payload)},
            "requester": {"email": ORDER["customer_email"]},
            "custom_fields": [{"id": ORDER_NUMBER_FIELD, "value": ORDER["number"]}],
            "tags": ["concierge", slug(payload["intent"]), payload["trigger"]],
        }},
        timeout=15,
    )
    r.raise_for_status()
    payload["delivered"] = True
    payload["reference"] = r.json()["ticket"]["id"]
    return payload


def slug(text):
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in text).split())


def ticket_html(payload):
    """The description a person at Weber Impressions reads. Who, what, why; the order as it
    stands; the whole conversation."""
    def e(text):
        # Zendesk links "#94105" to ticket 94105, which doesn't exist. Ticket text only.
        return html.escape(re.sub(r"#(?=\d)", "", text))

    summary = payload["summary"].strip()
    for prefix in ("The customer ", "Customer "):
        if summary.startswith(prefix):
            summary = summary[len(prefix):]
            break
    reason = payload["routing_reason"].strip().rstrip(".")
    reason = reason[0].lower() + reason[1:] if reason else reason
    if payload["trigger"] == "turn_limit":
        why = f"Concierge escalated after six turns without resolution: {e(reason)}."
    else:
        why = f"Concierge escalated because {e(reason)}."

    lines = "".join(
        f"<li>Publisher {l['publisher']} — {e(l['title'])} — "
        + (f"<code>{e(l['status'])}</code>" if l["status"].startswith("cancelled") else e(l["status"]))
        + "</li>"
        for l in payload["lines"]
    )
    turns = "".join(
        f"<li>{'Customer' if t['role'] == 'user' else 'Concierge'}: {e(t['text'])}</li>"
        for t in payload["transcript"]
    )
    placed = "August 17, 2026"
    return (
        f"<p>{e(payload['customer']['email'])} {e(summary)}</p>"
        f"<p>{why}</p>"
        f"<p><strong>Order {e(payload['customer']['order'])}</strong><br>{placed}</p>"  # no '#': Zendesk would link it as a ticket
        f"<ul>{lines}</ul><br>"
        f"<p>${payload['customer']['order_total_usd']:.2f} USD</p>"
        f"<p><strong>Conversation</strong></p>"
        f"<ul>{turns}</ul>"
    )
