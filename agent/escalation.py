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


def handoff(destination, intent, reason, summary, messages):
    payload = {
        "destination": destination,
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
    subdomain = os.environ.get("ZENDESK_SUBDOMAIN")
    email = os.environ.get("ZENDESK_EMAIL")
    token = os.environ.get("ZENDESK_API_TOKEN")
    if not (subdomain and email and token):
        payload["delivered"] = False
        payload["reference"] = None
        payload["note"] = "No Zendesk credentials configured. The interface shows the customer this payload; tell them the request couldn't be filed."
        print(f"[handoff → weber-impressions] NOT DELIVERED\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
        return payload

    body = "\n".join(f"{t['role']}: {t['text']}" for t in payload["transcript"])
    r = requests.post(
        f"https://{subdomain}.zendesk.com/api/v2/tickets.json",
        auth=(f"{email}/token", token),
        json={"ticket": {
            "subject": f"Order {ORDER['number']} — {payload['intent']}",
            "comment": {"body": f"{payload['summary']}\n\nRouting: {payload['routing_reason']}\n\n{body}"},
            "tags": ["concierge", payload["intent"]],
        }},
        timeout=15,
    )
    r.raise_for_status()
    payload["delivered"] = True
    payload["reference"] = r.json()["ticket"]["id"]
    return payload
