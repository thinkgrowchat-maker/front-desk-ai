# Front Desk AI 🛎️

An AI receptionist for small businesses. It answers customers' repetitive
questions instantly and accurately — grounded **only** in the business's own
information, with a built-in guardrail that hands off to a human instead of
guessing.

Built as a demo around a fictional restaurant, **The Copper Kettle**, but the
whole "brain" lives in one file ([`knowledge_base.py`](knowledge_base.py)) — swap
it for any business (salon, clinic, contractor, shop) and everything else works
unchanged.

**▶️ Live demo: https://front-desk-ai.onrender.com**
&nbsp;·&nbsp; *(free-tier hosted — the first load after a quiet spell may take ~30s to wake up)*

<!-- Add a screenshot of the running app here for your portfolio / GitHub:
     ![Front Desk AI](docs/screenshot.png) -->

## The problem it solves

Small-business owners are the receptionist, the marketer, and the entire ops
team. A huge share of their day is spent answering the same 20 questions —
hours, parking, reservations, "do you have vegan options?" — over email, DMs,
and the phone. A generic chatbot is worse than nothing, because it will happily
*make up* an answer about your allergy policy or your prices.

Front Desk AI is built the way a business actually needs it:

- **Retrieval-Augmented Generation (RAG).** Every question is first matched
  against the business's real knowledge base using vector similarity. Only the
  most relevant facts are handed to the model.
- **Grounded answers, with citations.** The model is instructed to answer *only*
  from retrieved facts and to cite which ones it used. The UI shows this live.
- **A human-handoff guardrail.** If the answer isn't in the knowledge base — or
  the question is high-stakes (severe allergies, custom event quotes,
  complaints, refunds) — it escalates to a person instead of guessing.

## How it works

```
Guest question
      │
      ▼
TF-IDF vector search  ──►  top matching knowledge-base entries (with scores)
      │
      ▼
LLM (Gemini / Claude)     ──►  answer grounded in those entries ONLY
      │                         + structured output: { answer, cited sources,
      ▼                                                 escalate?, reason }
Guest sees a warm, accurate answer — or a graceful handoff to the team.
```

- **Retrieval** ([`retrieval.py`](retrieval.py)) is real vector-space search
  (TF-IDF + cosine similarity) with **zero dependencies** — it runs offline and
  its scores are fully explainable, which is why the UI can show a live
  "Retrieval Inspector."
- **Grounding + guardrails** ([`server.py`](server.py)) drive the LLM with a
  strict system prompt and **structured outputs** (a JSON schema) so every reply
  is a clean, actionable object — including an explicit `escalate` decision.

## Run it

Requires only **Python 3.9+** — no `pip install`, no `npm install`.

```bash
cd front-desk-ai

# 1. (optional) add a key for live AI answers
cp .env.example .env      # then add a FREE Google Gemini key (no credit card)
                          # from https://aistudio.google.com/apikey
                          # — or an Anthropic Claude key if you prefer.

# 2. start it
python3 server.py         # → http://localhost:8000
```

The provider is auto-detected: a Gemini key runs on Google's **free tier**, an
Anthropic key runs on Claude. With **no key** it runs in **demo mode** — you
still see retrieval, the inspector, and the escalation guardrail working; the
wording just comes from a template instead of an LLM.

Check the retrieval engine on its own (no key needed):

```bash
python3 test_retrieval.py
```

## Things to try in the UI

| Ask this…                                   | What it demonstrates                         |
| ------------------------------------------- | -------------------------------------------- |
| "What time do you close on Sunday?"         | Grounded answer, cited source                |
| "Can I bring my dog?"                       | Retrieval picks the right entry              |
| "I have a severe peanut allergy — is that ok?" | Guardrail escalates a high-stakes question |
| "Can you book me for a wedding?"            | Escalates a custom-quote request             |
| "What's the wifi password?"                 | Not in the KB → refuses to guess, hands off  |

## Make it yours

1. Edit [`knowledge_base.py`](knowledge_base.py) with your own business's facts.
2. Change the name/voice in `BUSINESS` and the system prompt in `server.py`.
3. Deploy anywhere that runs Python (Render, Fly.io, a small VM).

## Tech

Python standard library · pluggable LLM (Google Gemini free tier **or** Anthropic
Claude) with structured JSON outputs · TF-IDF retrieval · vanilla HTML/CSS/JS
front end. No frameworks, no build step, no dependencies.
