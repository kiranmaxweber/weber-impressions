// Concierge. The browser holds the conversation and sends the whole list each turn; the
// server keeps nothing. The journey shortcuts populate the field without sending.

const SHORTCUTS = {
  aaa: "How long does shipping usually take from your publishers? I ordered three books last week and only two have shipping notifications.",
  bbb: "No need. Where do mine actually stand?",
  ccc: "One of those won't arrive in time.",
  ddd: "The third. I need it by September 1.",
  eee: "Yes, do that.",
  fff: "I still need a gift by September 1. Any recommendations?",
};
const ORDER = Object.keys(SHORTCUTS);

let messages = [];
let step = 0; // index into ORDER of the next shortcut to suggest

const conversation = document.getElementById("conversation");
const composer = document.getElementById("composer");
const input = document.getElementById("input");
const send = document.getElementById("send");
const hint = document.getElementById("hint");

function showHint() {
  if (step === 0) hint.textContent = "Type aaa to begin";
  else if (step < ORDER.length) hint.textContent = `Next: ${ORDER[step]}`;
  else hint.textContent = "";
}

function add(className, text) {
  const el = document.createElement("div");
  el.className = `turn ${className}`;
  el.textContent = text;
  conversation.appendChild(el);
  conversation.scrollTop = conversation.scrollHeight;
  return el;
}

// Typing a shortcut replaces it with the scripted message. Nothing is sent.
input.addEventListener("input", () => {
  const text = input.value.trim();
  if (SHORTCUTS[text]) input.value = SHORTCUTS[text];
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composer.requestSubmit();
  }
});

composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || send.disabled) return;

  if (step < ORDER.length && text === SHORTCUTS[ORDER[step]]) step += 1;
  showHint();

  add("you", text);
  messages.push({ role: "user", content: text });
  input.value = "";
  send.disabled = true;
  const pending = add("event", "Concierge is looking…");

  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    const data = await r.json();
    messages = data.messages;
    pending.remove();
    for (const ev of data.events) add("event", ev);
    add("assistant", data.reply);
    for (const h of data.handoffs) {
      if (h && h.delivered === false) {
        const pre = document.createElement("pre");
        pre.className = "handoff";
        pre.textContent = JSON.stringify(h, null, 2);
        conversation.appendChild(pre);
      }
    }
  } catch (err) {
    pending.remove();
    messages.pop();
    add("assistant", "Something went wrong on my side. Try that once more.");
  } finally {
    send.disabled = false;
    input.focus();
    conversation.scrollTop = conversation.scrollHeight;
  }
});

showHint();
input.focus();
