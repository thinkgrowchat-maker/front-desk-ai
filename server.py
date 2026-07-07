"""
server.py — the Front Desk AI backend.

A zero-dependency HTTP server (Python standard library only) that:
  1. Serves the chat UI from ./public
  2. Exposes POST /api/chat: retrieve relevant knowledge -> ask an LLM -> answer
  3. Enforces anti-hallucination guardrails: the model may ONLY answer from
     retrieved knowledge, and must escalate high-stakes questions to a human.

The LLM provider is auto-detected from whatever key is present:
  - ANTHROPIC_API_KEY  -> Anthropic Claude   (paid)
  - GEMINI_API_KEY     -> Google Gemini       (free tier, no credit card)
  - neither            -> "demo mode": retrieval + guardrail work, answers are
                          templated (no LLM call, so it costs nothing to run).

Run it:  python3 server.py   (then open http://localhost:8000)
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from knowledge_base import BUSINESS, KNOWLEDGE_BASE
from retrieval import build_index, search

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
PORT = int(os.environ.get("PORT", "8000"))
# Abuse protection for a public demo: cap live LLM calls per day so a burst of
# traffic can't exhaust the free-tier quota, and bound the input length.
DAILY_CAP = int(os.environ.get("DAILY_REQUEST_CAP", "200"))
MAX_MSG_LEN = 500
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #
def _load_env():
    """Minimal .env loader so we don't need python-dotenv."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if ANTHROPIC_KEY:
    PROVIDER, PROVIDER_LABEL = "claude", "Anthropic Claude"
    MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
elif GEMINI_KEY:
    PROVIDER, PROVIDER_LABEL = "gemini", "Google Gemini"
    MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
else:
    PROVIDER, PROVIDER_LABEL, MODEL = "demo", "Demo mode", ""

INDEX = build_index(KNOWLEDGE_BASE)

SYSTEM_PROMPT = f"""You are the AI front desk assistant for {BUSINESS['name']}, a \
{BUSINESS['tagline'].lower()}. You help guests on the restaurant's website.

Follow these rules strictly:
1. Answer ONLY using facts in the CONTEXT block provided in the user's message. \
The CONTEXT is retrieved from the restaurant's official knowledge base. Do not use \
any outside knowledge, assumptions, or general information about restaurants.
2. If the CONTEXT does not clearly contain the answer, do NOT guess. Set "escalate" \
to true and let the guest know you will connect them with the team.
3. Always escalate (escalate=true) for high-stakes questions, even when some \
context looks relevant: severe or specific food allergies and medical dietary \
needs, custom pricing or bookings for large private events, complaints, refunds, \
lost & found, or anything involving a guest's health or money beyond what is \
explicitly listed. For general dietary info that IS in the context (e.g. "we have \
vegan dishes"), you may answer, but briefly add that guests with serious allergies \
should confirm with staff.
4. Keep answers warm, concise, and specific — 1 to 3 sentences, in a friendly \
hospitality voice.
5. Put the ids of the CONTEXT entries you actually used in "used_source_ids". If \
you escalate because the information is not available, leave it empty.
6. When you escalate, "answer" is the friendly message shown to the guest, and \
"escalation_reason" is a short internal note for the staff.

Never invent hours, prices, menu items, or policies. It is always better to \
escalate to a human than to guess."""

# Structured-output schema (Anthropic / JSON Schema flavor).
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "used_source_ids": {"type": "array", "items": {"type": "string"}},
        "escalate": {"type": "boolean"},
        "escalation_reason": {"type": "string"},
    },
    "required": ["answer", "used_source_ids", "escalate", "escalation_reason"],
    "additionalProperties": False,
}

# The same schema in Gemini's (OpenAPI-subset) flavor.
GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": {"type": "STRING"},
        "used_source_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
        "escalate": {"type": "BOOLEAN"},
        "escalation_reason": {"type": "STRING"},
    },
    "required": ["answer", "used_source_ids", "escalate", "escalation_reason"],
}

# High-stakes triggers used only by the no-API-key "demo mode".
_ESCALATE_HINTS = (
    "allerg", "anaphyla", "epipen", "refund", "complaint", "sick", "wedding",
    "buyout", "buy out", "lost", "manager", "lawsuit",
)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
_usage = {"date": "", "count": 0}


def _rate_ok():
    """Simple in-memory daily cap on live LLM calls (resets at UTC midnight)."""
    today = date.today().isoformat()
    if _usage["date"] != today:
        _usage["date"], _usage["count"] = today, 0
    if _usage["count"] >= DAILY_CAP:
        return False
    _usage["count"] += 1
    return True


def answer_question(message, history):
    """Retrieve context, ask the active LLM to answer within it, format the reply."""
    hits = search(INDEX, message, top_k=3)
    sources = [
        {"id": h["doc"]["id"], "title": h["doc"]["title"], "score": round(h["score"], 3)}
        for h in hits
    ]

    if PROVIDER == "demo":
        return _demo_reply(message, hits, sources)

    if not _rate_ok():
        return _cap_reached(sources)

    context = "\n\n".join(
        f"[{h['doc']['id']}] {h['doc']['title']}\n{h['doc']['text']}" for h in hits
    ) or "(no relevant entries were found in the knowledge base)"

    try:
        if PROVIDER == "claude":
            parsed = _claude_generate(context, message, history)
        else:
            parsed = _gemini_generate(context, message, history)
    except RuntimeError as reason:
        return _handoff(sources, mode=PROVIDER, reason=str(reason))

    return {
        "answer": parsed.get("answer", ""),
        "escalate": bool(parsed.get("escalate")),
        "escalationReason": parsed.get("escalation_reason", ""),
        "usedSourceIds": parsed.get("used_source_ids", []),
        "sources": sources,
        "model": MODEL,
        "mode": "live",
    }


def _post_json(url, headers, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


# --- Anthropic Claude ------------------------------------------------------- #
def _claude_generate(context, message, history):
    messages = []
    for turn in history[-6:]:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(turn.get("content", ""))})
    messages.append(
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nGUEST QUESTION:\n{message}"}
    )

    body = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "output_config": {
            "effort": "low",
            "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA},
        },
        "messages": messages,
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
    }
    data = _request(ANTHROPIC_URL, headers, body)

    if data.get("stop_reason") == "refusal":
        raise RuntimeError("Declined by safety system")
    text = next(
        (b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"),
        "",
    )
    return _parse_or_raise(text)


# --- Google Gemini ---------------------------------------------------------- #
def _gemini_generate(context, message, history):
    contents = []
    for turn in history[-6:]:
        role = "model" if turn.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": str(turn.get("content", ""))}]})
    contents.append(
        {"role": "user", "parts": [{"text": f"CONTEXT:\n{context}\n\nGUEST QUESTION:\n{message}"}]}
    )

    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
            "responseSchema": GEMINI_SCHEMA,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    headers = {"content-type": "application/json", "x-goog-api-key": GEMINI_KEY}
    data = _request(url, headers, body)

    if data.get("promptFeedback", {}).get("blockReason"):
        raise RuntimeError("Declined by safety system")
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("No response from model")
    cand = candidates[0]
    if cand.get("finishReason") in ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"):
        raise RuntimeError("Declined by safety system")
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    return _parse_or_raise(text)


# --- shared helpers --------------------------------------------------------- #
def _request(url, headers, body):
    try:
        return _post_json(url, headers, body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        print(f"[{PROVIDER}] HTTP {e.code}: {detail}")
        raise RuntimeError(f"AI request failed (HTTP {e.code})")
    except Exception as e:  # network / timeout
        print(f"[{PROVIDER}] request failed: {e}")
        raise RuntimeError("AI request failed (network)")


def _parse_or_raise(text):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        raise RuntimeError("Unparseable model output")


def _handoff(sources, mode, reason):
    """Graceful escalation. `reason` is the internal staff note; the guest sees a
    friendly, consistent hand-off message."""
    return {
        "answer": (
            "I want to make sure you get the right answer, so let me connect you "
            f"with our team — call {BUSINESS['phone']} or email {BUSINESS['email']} "
            "and we'll be glad to help."
        ),
        "escalate": True,
        "escalationReason": reason,
        "usedSourceIds": [],
        "sources": sources,
        "model": MODEL,
        "mode": mode,
    }


def _cap_reached(sources):
    """Friendly response when the public demo hits its daily free-usage cap."""
    return {
        "answer": (
            "Thanks for trying the live demo! It's reached today's free-usage "
            "limit, so live answers are paused until tomorrow. In the meantime you "
            f"can reach the team at {BUSINESS['phone']}."
        ),
        "escalate": True,
        "escalationReason": "Daily demo request cap reached",
        "usedSourceIds": [],
        "sources": sources,
        "model": MODEL,
        "mode": "capped",
    }


def _demo_reply(message, hits, sources):
    """Runs without any API key: shows retrieval + a grounded, templated answer."""
    lowered = message.lower()
    if not hits:
        return _handoff(sources, mode="demo", reason="No matching knowledge in the KB")
    if any(hint in lowered for hint in _ESCALATE_HINTS):
        return _handoff(sources, mode="demo",
                        reason="High-stakes question (allergy/quote/complaint)")
    top = hits[0]["doc"]
    return {
        "answer": top["text"],
        "escalate": False,
        "escalationReason": "",
        "usedSourceIds": [top["id"]],
        "sources": sources,
        "model": MODEL,
        "mode": "demo",
    }


# --------------------------------------------------------------------------- #
# HTTP handler
# --------------------------------------------------------------------------- #
_CONTENT_TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the console clean
        pass

    def _send_json(self, obj, status=200):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/api/health":
            return self._send_json({
                "ok": True,
                "business": BUSINESS["name"],
                "provider": PROVIDER,
                "providerLabel": PROVIDER_LABEL,
                "model": MODEL,
                "liveAI": PROVIDER != "demo",
                "kbEntries": len(KNOWLEDGE_BASE),
            })

        rel = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        target = (PUBLIC / rel).resolve()
        if PUBLIC not in target.parents or not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("content-type", _CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("content-length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "invalid JSON"}, status=400)

        message = str(data.get("message", "")).strip()[:MAX_MSG_LEN]
        history = data.get("history", [])
        if not message:
            return self._send_json({"error": "message is required"}, status=400)
        if not isinstance(history, list):
            history = []

        self._send_json(answer_question(message, history))


def main():
    mode = f"LIVE · {PROVIDER_LABEL}" if PROVIDER != "demo" else "DEMO (no API key — retrieval only)"
    print("\n  Front Desk AI  ·  " + BUSINESS["name"])
    print("  " + "-" * 44)
    print(f"  Provider     : {mode}")
    if MODEL:
        print(f"  Model        : {MODEL}")
    print(f"  KB entries   : {len(KNOWLEDGE_BASE)}")
    print(f"  Open         : http://localhost:{PORT}\n")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
