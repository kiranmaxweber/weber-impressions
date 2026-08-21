"""Tool definitions and dispatch.

The model decides what to do; this file decides what's allowed. The one gate that matters is
in cancel_line: a line that has been charged — which means it has shipped — cannot be
cancelled, whatever the model asks for.
"""

import json
import os

import requests

from agent.escalation import handoff
from agent.order import ORDER, line_for
from publishers import publisher_1, publisher_2, publisher_3

FAQ_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "faqs")
ADAPTERS = {1: publisher_1, 2: publisher_2, 3: publisher_3}
DESTINATIONS = ["weber-impressions", "publisher-1", "publisher-2", "publisher-3"]

TOOLS = [
    {
        "name": "read_faq",
        "description": "Read one document from the FAQs. Pick the owner by who the question belongs to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "enum": DESTINATIONS},
                "file": {"type": "string", "description": "Filename from the manifest, e.g. shipping.md"},
            },
            "required": ["owner", "file"],
        },
    },
    {
        "name": "check_order",
        "description": "Fetch the live status of this order's line at one publisher. Publisher 3 returns its confirmation email rather than fields.",
        "input_schema": {
            "type": "object",
            "properties": {"publisher": {"type": "integer", "description": "1, 2, or 3"}},
            "required": ["publisher"],
        },
    },
    {
        "name": "cancel_line",
        "description": "Cancel one line of the order. Only possible before it ships; the tool refuses otherwise. Confirm with the customer first.",
        "input_schema": {
            "type": "object",
            "properties": {"publisher": {"type": "integer"}},
            "required": ["publisher"],
        },
    },
    {
        "name": "escalate",
        "description": "Hand the conversation to the people who own the issue. Recommendations and storefront matters go to weber-impressions; a publisher's policy, returns, or damage go to that publisher.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "enum": DESTINATIONS},
                "intent": {"type": "string", "description": "Short label, e.g. recommendation, return, damage, policy-exception"},
                "reason": {"type": "string", "description": "Why this destination owns it"},
                "summary": {"type": "string", "description": "What the person picking this up needs to know"},
            },
            "required": ["destination", "intent", "reason", "summary"],
        },
    },
    {
        "name": "request_human",
        "description": "The customer asked for a person. Call this immediately; no questions first.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def describe(name, args):
    """What the UI shows while the tool runs."""
    if name == "read_faq":
        return f"Reading {args.get('owner')}/{args.get('file')}…"
    if name == "check_order":
        return f"Checking Publisher {args.get('publisher')}…"
    if name == "cancel_line":
        return f"Cancelling at Publisher {args.get('publisher')}…"
    return "Opening a request…"


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


def dispatch(name, args, messages):
    """Run one tool. Returns (content, is_error). Errors go back to the model as text, never raised."""
    try:
        if name == "read_faq":
            return read_faq(args["owner"], args["file"]), False
        if name == "check_order":
            return check_order(int(args["publisher"]), messages), False
        if name == "cancel_line":
            return cancel_line(int(args["publisher"]), messages), False
        if name == "escalate":
            return handoff(args["destination"], args["intent"], args["reason"], args["summary"], messages), False
        if name == "request_human":
            return handoff("weber-impressions", "customer-requested-human",
                           "The customer asked for a person.", "Customer asked to speak to someone.", messages), False
        return f"No tool named {name}.", True
    except ToolError as e:
        return str(e), True
    except requests.RequestException as e:
        return f"Couldn't reach the publisher's system: {e.__class__.__name__}.", True


class ToolError(Exception):
    pass


def read_faq(owner, file):
    path = os.path.normpath(os.path.join(FAQ_DIR, owner, file))
    if not path.startswith(FAQ_DIR) or not os.path.isfile(path):
        raise ToolError(f"No document {owner}/{file}. Only files listed in the manifest exist.")
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_order(publisher, messages):
    line = line_for(publisher)
    if line is None:
        raise ToolError(f"Publisher {publisher} is not part of order {ORDER['number']}. This order has lines from Publishers 1, 2, and 3.")
    record = ADAPTERS[publisher].lookup(ORDER["number"])
    if record is None:
        raise ToolError(f"Publisher {publisher} has no record of order {ORDER['number']}.")
    if publisher in cancelled_lines(messages):
        record["status"] = "cancelled"
        record["note"] = "Cancelled in this conversation."
    return record


def cancel_line(publisher, messages):
    line = line_for(publisher)
    if line is None:
        raise ToolError(f"Publisher {publisher} is not part of order {ORDER['number']}.")
    if publisher in cancelled_lines(messages):
        raise ToolError(f"The Publisher {publisher} line is already cancelled.")

    # The gate. Charged means shipped — money has moved and a parcel is in transit. Not ours
    # to undo; that's the publisher's returns policy. Checked against our own record first,
    # then the publisher's, so a stale flag on either side still blocks.
    if line["charged"]:
        raise ToolError(f"The Publisher {publisher} line has shipped and been charged. It can't be cancelled; Publisher {publisher}'s returns policy applies.")
    record = ADAPTERS[publisher].lookup(ORDER["number"])
    if record and record.get("status") in ("shipped", "delivered"):
        raise ToolError(f"Publisher {publisher} reports this line as {record['status']}. It can't be cancelled.")

    # Reversible, unshipped, uncharged: the agent may act. The publisher's API is read-only,
    # so the request is logged rather than written; the transcript holds the cancellation.
    print(f"[cancel → publisher-{publisher}] order {ORDER['number']}, {line['title']} (stub — request logged)")
    return {
        "publisher": publisher,
        "title": line["title"],
        "status": "cancelled",
        "charged": False,
        "refund_due": 0,
        "note": "Nothing was charged for this line, so there is nothing to refund.",
    }


def to_text(result):
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=1)
