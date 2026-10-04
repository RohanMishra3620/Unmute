# Unmute 🎙️

**Unmute** is a privacy-focused, AI-guided emotional reflection web application. It gives users a short **5-minute anonymous conversation** to express how they are feeling and then generates a structured, **non-diagnostic reflection report** containing emotional signals, topics discussed, safety observations, and practical next steps.

> **Important:** Unmute is an emotional-support and reflection tool. It is **not** a doctor, therapist, diagnostic system, or emergency service. The project has not been clinically validated.

## Live Project

- **Frontend:** https://unmute-frontend-tau.vercel.app/
- **Backend health check:** https://unmute-backend-btlo.onrender.com/health
- **GitHub repository:** https://github.com/RohanMishra3620/Unmute

## What Problem Does Unmute Solve?

People do not always need a long form, complicated dashboard, or an immediate diagnosis. Sometimes they first need a private space to put their thoughts into words.

Unmute is designed around that idea. A user starts an anonymous session, talks with the system for up to five minutes, and receives a simple reflection of the conversation. The application attempts to recognize emotional patterns and safety-related signals while deliberately avoiding medical diagnosis.

## How It Works

```text
User
  │
  ▼
Static Frontend (HTML / CSS / JavaScript)
  │
  │ HTTPS REST API
  ▼
Flask Backend
  │
  ▼
Regex / Signal Detection
  │
  ▼
Safety Agent  ──────► Crisis / high-concern response when required
  │
  ▼
Analysis Agent
  │
  ▼
Knowledge Agent
  │
  ▼
Conversation Agent
  │
  ▼
SQLite Session Storage
  │
  ▼
Report Agent
  │
  ▼
Non-diagnostic Reflection Report
```

For each normal message, the backend pipeline is approximately:

```text
Regex Engine → Safety Agent → Analysis Agent → Knowledge Agent → Conversation Agent → Store Result
```

**Safety has the highest priority.** If a message is classified as `HIGH_CONCERN` or `CRISIS`, the normal conversation flow is bypassed and the Safety Agent provides a direct safety-focused response. An optional LLM is allowed to increase a detected risk level, but it cannot lower a risk level already detected by the deterministic safety layer.

## Main Features

- **Anonymous 5-minute sessions** with no account required in the current prototype.
- **Safety-first message processing** using deterministic regex rules and a dedicated Safety Agent.
- **Multi-agent backend architecture** for safety, emotional analysis, knowledge retrieval, conversation, and reporting.
- **Optional LLM integration** for richer analysis and responses.
- **Rule-based fallback mode**, so the application can run without an LLM API key.
- **Structured reflection reports** showing emotional state, dominant emotions, topics, positive signals, concerns, safety level, and suggested next steps.
- **Configurable emergency contacts** and emergency messaging.
- **Session deletion** so a user can delete the stored session from the report page.
- **Automated tests** for APIs, safety behavior, regex analysis, conversations, session handling, and expiry.
- **Separated frontend and backend deployments**, reducing coupling between the UI and API.

## User Flow

1. The user opens the Unmute frontend.
2. Clicking **Start Session** creates a new anonymous backend session.
3. Unmute opens with a supportive introductory message and suggested conversation prompts.
4. Every user message is checked for emotional and safety signals.
5. Safe conversations continue through the analysis, knowledge, and conversation pipeline.
6. High-risk messages are handled by the Safety Agent with higher priority than normal conversation generation.
7. The session ends manually or automatically when its timer expires.
8. The Report Agent creates a reflection report.
9. The user can review the report and optionally delete the session data.

## Reflection Report

A completed session can contain:

- Overall emotional state
- Dominant emotions
- Emotional intensity scores
- Main conversation topics
- Positive signals
- Areas to keep an eye on
- Safety/risk level
- Suggested next steps
- A plain-language conversation summary

Every report includes a disclaimer that it is an **AI-generated reflection, not a medical diagnosis**.

## Safety Design

Unmute uses the following risk levels:

```text
SAFE
LOW_CONCERN
MODERATE_CONCERN
HIGH_CONCERN
CRISIS
```

The safety system is intentionally separated from normal response generation. The deterministic layer identifies configured risk patterns first. The Safety Agent then decides whether the normal conversation pipeline is allowed to continue.

For high-concern situations, the application can display configured emergency information. The default configuration includes India's emergency number **112** and **Tele-MANAS 14416**, but these values can be changed through environment variables for other deployments.

> Before using this project with real users, the safety rules, crisis wording, emergency resources, privacy model, and report language should be reviewed by qualified mental-health and safety professionals.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python, Flask |
| API | REST / JSON |
| Database | SQLite |
| AI integration | OpenAI-compatible API or Anthropic (optional) |
| Backend server | Gunicorn |
| Frontend deployment | Vercel |
| Backend deployment | Render |
| Testing | Pytest |

## Project Structure

```text
Unmute/
├── backend/
│   ├── agents/
│   │   ├── analysis_agent.py
│   │   ├── conversation_agent.py
│   │   ├── knowledge_agent.py
│   │   ├── report_agent.py
│   │   └── safety_agent.py
│   ├── knowledge_base/
│   │   └── mental_health.json
│   ├── models/
│   │   ├── database.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── orchestrator.py
│   │   ├── regex_engine.py
│   │   └── session_manager.py
│   ├── app.py
│   ├── config.py
│   └── requirements.txt
│
├── frontend/
│   ├── css/
│   │   └── app.css
│   ├── img/
│   │   └── hero.jpg
│   ├── js/
│   │   ├── app.js
│   │   ├── chat.js
│   │   ├── config.js
│   │   └── report.js
│   ├── index.html
│   ├── chat.html
│   ├── report.html
│   └── about.html
│
├── tests/
│   ├── test_api.py
│   ├── test_conversation.py
│   ├── test_regex_engine.py
│   ├── test_safety_agent.py
│   └── test_session_manager.py
│
├── .env.example
├── pytest.ini
├── run-backend.bat
├── run-backend.ps1
├── run-frontend.bat
├── run-frontend.ps1
└── README.md
```

## Backend Agents

### Safety Agent

Has the highest priority in the system. It handles high-concern/crisis situations and prevents a normal conversational response from overriding safety behavior.

### Analysis Agent

Converts deterministic regex signals and, when configured, optional LLM analysis into structured information such as emotion, intensity, confidence, signals, and a possible risk hint. It is designed not to diagnose the user.

### Knowledge Agent

Retrieves relevant coping/support information from the local `mental_health.json` knowledge base according to detected signals.

### Conversation Agent

Generates the normal supportive conversational reply and suggestion chips. Its output policy restricts diagnoses, medication advice, and claims of being a therapist.

### Report Agent

Aggregates the session's analyses and messages into the final reflection report. It can use an LLM for the summary when available and falls back to deterministic report generation otherwise.

## REST API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend liveness check |
| `POST` | `/api/session/start` | Start a new anonymous session |
| `POST` | `/api/chat` | Send a message to an active session |
| `POST` | `/api/session/end` | End the session and generate its report |
| `GET` | `/api/session/<id>` | Get current session state and messages |
| `GET` | `/api/session/<id>/report` | Get the generated reflection report |
| `DELETE` | `/api/session/<id>` | Delete the session and associated data |

### Example: Start a Session

```bash
curl -X POST https://unmute-backend-btlo.onrender.com/api/session/start
```

A successful response contains a session ID, configured duration, opening message, and suggested replies.

### Example: Send a Message

```bash
curl -X POST https://unmute-backend-btlo.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"YOUR_SESSION_ID","message":"I have been feeling stressed lately"}'
```

## Run Locally

### 1. Clone the Repository

```bash
git clone https://github.com/RohanMishra3620/Unmute.git
cd Unmute
```

### 2. Create a Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables

Copy the example configuration:

```bash
cp .env.example .env
```

On Windows Command Prompt you can use:

```bat
copy .env.example .env
```

An LLM key is **not required** to start the project. Without one, Unmute uses its built-in rule-based fallback behavior.

### 5. Start the Backend

From the project root:

```bash
python -m backend.app
```

Backend:

```text
http://127.0.0.1:5000
```

Health check:

```text
http://127.0.0.1:5000/health
```

### 6. Configure the Frontend for Local Development

In `frontend/js/config.js`:

```js
const API_URL = "http://127.0.0.1:5000";
```

### 7. Start the Frontend

```bash
cd frontend
python -m http.server 5500
```

Then open:

```text
http://localhost:5500
```

## Environment Variables

| Variable | Purpose | Default/Example |
| --- | --- | --- |
| `LLM_PROVIDER` | LLM provider | `openai` |
| `LLM_API_KEY` | API key for optional LLM | Empty |
| `LLM_MODEL` | Model used by the LLM service | Empty |
| `LLM_BASE_URL` | OpenAI-compatible API base URL | `https://api.openai.com/v1` |
| `LLM_TIMEOUT` | LLM request timeout | `12` |
| `SESSION_SECONDS` | Session duration | `300` |
| `PORT` | Backend port | `5000` |
| `EMERGENCY_CONTACTS` | Semicolon-separated emergency contacts | Configurable |
| `EMERGENCY_MESSAGE` | Custom emergency message | Configurable |
| `FRONTEND_ORIGIN` | Allowed production frontend origin(s) for CORS | Empty |
| `DB_PATH` | Optional absolute SQLite database path | `backend/unmute.db` |

Never expose `LLM_API_KEY` or other backend secrets in frontend JavaScript.

## Running Tests

From the project root:

```bash
python -m pytest -q
```

The current test suite covers important behavior including API validation, conversation flows, regex signal detection, safety handling, session timing/expiry, report generation, invalid sessions, and deletion.

## Deployment

### Backend — Render

Current backend:

```text
https://unmute-backend-btlo.onrender.com
```

Recommended Render configuration:

```text
Build Command: pip install -r backend/requirements.txt
Start Command: gunicorn "backend.app:create_app()"
Root Directory: project root
```

Set the production frontend origin:

```env
FRONTEND_ORIGIN=https://unmute-frontend-tau.vercel.app
```

Add optional `LLM_*`, emergency-contact, session, and database settings through Render environment variables rather than committing secrets.

### Frontend — Vercel

Current frontend:

```text
https://unmute-frontend-tau.vercel.app/
```

The frontend is static, so Vercel can deploy the `frontend` directory directly.

For production, `frontend/js/config.js` must point to the Render API:

```js
const API_URL = "https://unmute-backend-btlo.onrender.com";
```

Suggested Vercel settings:

```text
Root Directory: frontend
Framework Preset: Other
Build Command: none
Output Directory: .
```

## Database

The current version uses **SQLite**. It stores:

- Sessions
- Conversation messages
- Per-message analyses
- Generated reports

SQLite is appropriate for the current prototype/testing stage. For a production system with multiple instances or stronger persistence requirements, migrate to a managed database such as PostgreSQL.

## Privacy and Production Considerations

The application is intentionally described as anonymous because the current flow does not require a user account. However, deploying an emotional-support application creates significant privacy and security responsibilities.

Before production use, consider adding:

- A clear data-retention and deletion policy
- Encryption and secure secret management
- Rate limiting and abuse protection
- Production-grade persistent database storage
- Logging rules that avoid unnecessary sensitive conversation content
- Security and privacy review
- Clinical review of safety logic and crisis wording
- Country-aware emergency resources
- Monitoring and failure handling for external AI services
- Appropriate consent, terms, and privacy notices

## Current Limitations

- This is a prototype, not a clinically validated mental-health system.
- Emotional analysis can be incorrect or incomplete.
- Rule-based detection cannot understand every context, language, slang term, or indirect expression.
- Optional LLM output can also make mistakes.
- SQLite is not the intended long-term database for a horizontally scaled production deployment.
- Emergency resources need to be configured appropriately for the user's country/region.
- The system must not be used as a replacement for professional mental-health or emergency care.

## Future Improvements

Potential next steps for the project include PostgreSQL/Supabase migration, stronger privacy controls, rate limiting, improved multilingual signal detection, more extensive safety testing, better observability, accessibility testing, and professional review of mental-health content and crisis flows.

## Author

**Rohan Mishra**

GitHub: https://github.com/RohanMishra3620

## Disclaimer

Unmute is an experimental AI-assisted emotional reflection project built for support, learning, and development purposes. It does not provide medical advice, diagnosis, treatment, or emergency services. If someone may be in immediate danger, they should contact the appropriate local emergency service or qualified crisis support service.
