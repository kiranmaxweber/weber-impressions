"""Serves the static screens and one endpoint: POST /chat, which streams.

The browser never talks to the model. It sends the message list here, the agent loop runs
with the key server-side, and the updated list goes back.
"""

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

from agent.loop import run_turn  # noqa: E402 — needs the key loaded first

STATIC = os.path.join(HERE, "static")
PORT = int(os.environ.get("PORT", 8000))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC, **kwargs)

    def do_POST(self):
        """POST /chat. The response is newline-delimited JSON: one {"event": ...} line per
        tool call as it happens, then one {"reply", "messages", "handoffs"} line at the end.
        Streaming exists so the browser can show what the agent is doing while it does it."""
        if self.path != "/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.end_headers()

        def line(obj):
            self.wfile.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
            self.wfile.flush()

        try:
            reply, messages, events, handoffs = run_turn(messages, on_event=lambda e: line({"event": e}))
            line({"reply": reply, "messages": messages, "handoffs": handoffs})
        except Exception as e:  # the reviewer sees one line, never a stack trace in the chat
            print(f"[chat] {e.__class__.__name__}: {e}")
            line({"reply": "Something went wrong on my side. Try that once more, or ask for a person.",
                  "messages": messages[:-1], "handoffs": []})

    def end_headers(self):
        # Static files are never cached: a reviewer who pulls a change sees it on reload.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "POST" in fmt % args or "chat" in fmt % args:
            super().log_message(fmt, *args)


if __name__ == "__main__":
    print(f"Weber Impressions at http://localhost:{PORT}")
    ThreadingHTTPServer(("localhost", PORT), Handler).serve_forever()
