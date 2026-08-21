"""The agent loop.

One turn: call the model with the system prompt and tools. If it calls a tool, run it, hand
the result back, and call again. If it answers, asks a question, or has handed off, stop.
Four outcomes; only the tool call loops.

Session state is the message list. The browser holds it and sends it back every turn; the
server keeps nothing.
"""

import sys

import anthropic
from dotenv import load_dotenv

from agent.escalation import stalled
from agent.prompts import BACKSTOP, SYSTEM
from agent.tools import TOOLS, describe, dispatch, to_text

load_dotenv()  # ANTHROPIC_API_KEY from .env; the SDK reads it from the environment

MODEL = "claude-sonnet-5"
MAX_TOOL_ROUNDS = 8

client = anthropic.Anthropic()


def run_turn(messages):
    """messages: the conversation so far, ending with the customer's new message.
    Returns (reply, messages, events, handoffs). events is what each tool call was, for the
    UI; handoffs is any escalation payload produced this turn, so the UI can show it."""
    events = []
    handoffs = []

    if stalled(messages):
        events.append("Opening a request…")
        handoffs.append(backstop(messages))  # the loop below then phrases the reply

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
        )
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in response.content]})

        if response.stop_reason != "tool_use":
            break  # answered, asked a clarifying question, or finished a handoff

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            events.append(describe(block.name, block.input))
            content, is_error = dispatch(block.name, block.input, messages)
            if block.name in ("escalate", "request_human") and not is_error:
                handoffs.append(content)
            result = {"type": "tool_result", "tool_use_id": block.id, "content": to_text(content)}
            if is_error:
                result["is_error"] = True
            results.append(result)
        messages.append({"role": "user", "content": results})
    else:
        messages.append({"role": "assistant", "content": [{"type": "text", "text": "I've gone round on this without getting anywhere. Let me put you in front of a person."}]})

    reply = "".join(b["text"] for b in messages[-1]["content"] if b.get("type") == "text")
    return reply, messages, events, handoffs


def backstop(messages):
    """Code decided it's time; the model decides how it's said. One call with the escalate
    tool forced, so the destination, summary, and reason are the model's. The payload records
    trigger=turn_limit so a forced handoff is never mistaken for a chosen one."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM + BACKSTOP,
        tools=TOOLS,
        tool_choice={"type": "tool", "name": "escalate"},
        messages=messages,
    )
    messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in response.content]})
    results = []
    payload = None
    for block in response.content:
        if block.type == "tool_use":
            payload, is_error = dispatch(block.name, block.input, messages, trigger="turn_limit")
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": to_text(payload)})
    messages.append({"role": "user", "content": results})
    return payload

if __name__ == "__main__":
    # A terminal session, for testing the loop without the browser.
    messages = []
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        print(f"\n> {text}")
        messages.append({"role": "user", "content": text})
        reply, messages, events, handoffs = run_turn(messages)
        for e in events:
            print(f"  [{e}]")
        print(reply)
