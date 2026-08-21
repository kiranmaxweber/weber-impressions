"""Handoff to a person. The payload keeps its shape; the destination varies by who owns the issue.

Weber Impressions goes to a real Zendesk trial when credentials are configured. The three
publisher destinations are stubs that log. One real, two mocked — and when no Zendesk token
is present, the Weber Impressions handoff is returned undelivered with the payload shown,
never silently dropped.
"""

import json
import os

import requests

from agent.order import ORDER


def transcript(messages):
    """Plain turns only. Tool calls and results stay out of the ticket."""
    turns = []
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


def handoff(destination, intent, reason, summary, messages, trigger="model"):
    """trigger is "model" when the model chose to escalate, "turn_limit" when code forced it.
    A forced handoff must be distinguishable from a chosen one in the ticket."""
    payload = {
        "destination": destination,
        "trigger": trigger,
        "routing_reason": reason,
        "intent": intent,
        "summary": summary,
        "customer": {"order": ORDER["number"], "order_total_usd": ORDER["total_usd"]},
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

    body = "\n".join(f"{t['role']}: {t['text']}" for t in payload["transcript"])
    r = requests.post(
        f"{base}/api/v2/tickets.json",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"ticket": {
            "subject": f"Order {ORDER['number']} — {payload['intent']}",
            "comment": {"body": f"{payload['summary']}\n\nRouting: {payload['routing_reason']} (trigger: {payload['trigger']})\n\n{body}"},
            "tags": ["concierge", payload["intent"], payload["trigger"]],
        }},
        timeout=15,
    )
    r.raise_for_status()
    payload["delivered"] = True
    payload["reference"] = r.json()["ticket"]["id"]
    return payload
