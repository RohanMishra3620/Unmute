# Unmute

A short, private, AI-guided 5-minute conversation that helps people reflect on how they feel, followed by a structured (non-diagnostic) reflection report.
Flask + plain CSS + SQLite. Works out of the box with no API key; plug in an LLM through `.env` for richer replies.

> Unmute is a general emotional-support tool. It is not a doctor, therapist or emergency service, and it has not been clinically validated.
> Have a qualified clinician review the safety logic, wording and crisis resources before real users rely on it.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # optional; edit crisis contacts and LLM settings
python app.py               # http://127.0.0.1:5000
```

The pages load the Inter font from Google Fonts (a system font is used if offline). Everything else runs locally; Tailwind is no longer used.

## Tests

```bash
python -m pytest -q
```

Covers normal / stress / anxiety / sleep / high-risk messages, regex engine, safety agent, session timer and expiry, report generation, invalid session ID, empty message and session deletion.

## Structure

```
app.py                 Flask routes + error handling
config.py              env-driven settings (LLM, session length, emergency contacts)
agents/                conversation, analysis, safety, knowledge, report
services/              orchestrator, regex_engine, session_manager, llm_service
models/                SQLite schema + request validation
knowledge_base/        mental_health.json (16 topics)
templates/, static/    UI: landing, chat, report, about (static/css/app.css holds the colour/font tokens; static/img/hero.jpg is the background)
tests/
```

## Agentic architecture

`services/orchestrator.py` runs one pipeline per message: **regex engine -> Safety agent -> Analysis agent -> Knowledge agent -> Conversation agent -> store**.

- **Safety agent** has absolute priority. If it flags `HIGH_CONCERN` or `CRISIS`, the normal conversation agent is never called; the user gets a calm, direct crisis reply and the UI shows the emergency banner. After a crisis message, the next reply is also handled by the safety agent (a safety check-in).
- **Analysis agent** returns `{emotion, intensity, confidence, signals, needs_followup}` from regex signals, optionally refined by the LLM. An LLM can only *escalate* safety risk, never lower it.
- **Knowledge agent** retrieves coping tips from the local JSON so replies use stored content, not invented facts.
- **Conversation agent** writes 1-3 short sentences. LLM output is trimmed and checked against an output policy (no diagnoses, medication, or claims to be a therapist/human); on failure it falls back to rule-based replies.
- **Report agent** builds the final report (below).

## Regex safety layer

`services/regex_engine.py` holds categorized patterns (emotions, topics, `suicide`, `self_harm`, `harm_others`, `immediate_danger`, `crisis_intent`, `hopelessness`) and returns `{categories, matched_patterns, risk_level}`. Risk levels: `SAFE`, `LOW_CONCERN`, `MODERATE_CONCERN`, `HIGH_CONCERN`, `CRISIS`.
It is deliberately over-sensitive (e.g. "I would never hurt myself" still triggers), because a false alarm is better than a missed one. Regex is only the first layer; it cannot catch every phrasing, which is why the optional LLM layer can escalate.

## 5-minute session flow

1. `POST /api/session/start` stores `started_at` using the **server clock** and returns an anonymous session ID.
2. The browser shows a countdown, re-synced from the server after each reply.
3. Every `/api/chat` call re-checks the server clock. After 5 minutes it returns `410`, closes the session and generates the report; editing JavaScript cannot extend the session.
4. At 0:00, or on "End session", the page calls `/api/session/end` and opens `/report/<id>`.
5. "Delete Session" removes the session, messages, analyses and report.

## Report pipeline

When a session closes, the report agent aggregates stored per-message analyses: dominant emotions (intensity-weighted), main topics, positive signals, concerns, highest risk level, KB-based next steps, and a summary (LLM if configured, else a template). All wording is "the conversation contained signs of...", never a diagnosis. LLM summaries pass the same output policy.

## API

`POST /api/session/start` · `POST /api/chat` · `POST /api/session/end` · `GET /api/session/<id>/report` · `GET /api/session/<id>` (state) · `DELETE /api/session/<id>`

## Configuration

See `.env.example`. `LLM_PROVIDER` is `openai` (any OpenAI-compatible endpoint via `LLM_BASE_URL`) or `anthropic`. Leave `LLM_API_KEY`/`LLM_MODEL` empty for the offline fallback.
`EMERGENCY_CONTACTS` (`Label:number;Label:number`) and `EMERGENCY_MESSAGE` are configurable per country. If an LLM is enabled, user messages are sent to that provider.

## Before production

Add authentication/rate limiting, HTTPS, a production WSGI server, a data-retention policy, and a clinical review.

## Therapist-style replies (never the same twice)

`agents/conversation_agent.py` has two paths with the same rules (simple Indian English, no diagnosis, one easy question per turn):

1. **With an LLM** (set `LLM_API_KEY` + `LLM_MODEL` in `.env`): every reply is written fresh by the model. The prompt includes the session stage
   (open -> explore -> feel -> help -> close), the detected emotion, coping notes from the knowledge base and the replies already given.
   Output that repeats an earlier reply or breaks the output policy is discarded and the offline path is used instead.
2. **Offline** (no key): replies are built from many small parts (acknowledgement + the person's own words + one question or one coping step).
   Any sentence already said in the session is skipped, so nothing repeats.

Quick-reply buttons under the chat come from the server (`suggestions` in `/api/chat`), so people can answer with one tap.
New signals for this audience: `case_stress` (court / police / compensation), `fear`, `shame_guilt`, `trauma_memory`.

Examples for `.env`:

```
# Anthropic
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=<model name from your Anthropic console>

# Any OpenAI-compatible API (OpenAI, Gemini's OpenAI endpoint, Groq, Ollama ...)
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=...
LLM_MODEL=...
```
