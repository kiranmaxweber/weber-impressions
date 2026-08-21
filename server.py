"""Serves the static screens and one endpoint: POST /chat.

The browser never talks to the model. It sends the message list here, the agent loop runs
with the key server-side, and the updated list goes back.
"""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

from agent.loop import run_turn  # noqa: E402 — needs the key loaded first

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PORT = 8000


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC, **kwargs)

    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])
        try:
            reply, messages, events, handoffs = run_turn(messages)
            payload = {"reply": reply, "messages": messages, "events": events, "handoffs": handoffs}
        except Exception as e:  # the reviewer sees one line, never a stack trace in the chat
            print(f"[chat] {e.__class__.__name__}: {e}")
            payload = {"reply": "Something went wrong on my side. Try that once more, or ask for a person.", "messages": messages[:-1], "events": [], "handoffs": []}
        out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, fmt, *args):
        if "POST" in fmt % args or "chat" in fmt % args:
            super().log_message(fmt, *args)


if __name__ == "__main__":
    print(f"Weber Impressions at http://localhost:{PORT}")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
