from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.config import Config
from backend.models.schemas import ValidationError, validate_message, validate_session_id
from backend.services.orchestrator import Orchestrator
from backend.services.session_manager import SessionActive, SessionClosed, SessionExpired, SessionNotFound


def create_app(overrides=None):
    cfg = Config.as_dict()
    cfg.update(overrides or {})
    app = Flask(__name__)
    app.config.update(cfg)
    app.orchestrator = orch = Orchestrator(cfg)

    # CORS: allow configured frontend origin(s). Never use "*" in production.
    origins = []
    raw = (cfg.get("FRONTEND_ORIGIN") or "").strip()
    if raw:
        origins.extend(o.strip() for o in raw.split(",") if o.strip())
    # Local static servers (python -m http.server 5500, Live Server, etc.)
    for o in (
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ):
        if o not in origins:
            origins.append(o)
    CORS(
        app,
        origins=origins,
        methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        supports_credentials=False,
    )

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")
        return data

    def fail(code, key, msg, sid=None):
        out = {"error": key, "message": msg}
        if sid:
            out["session_id"] = sid
        return jsonify(out), code

    @app.errorhandler(ValidationError)
    def _invalid(e):
        return fail(400, "invalid_request", str(e))

    @app.errorhandler(SessionNotFound)
    def _missing(e):
        return fail(404, "session_not_found", "Session not found.")

    @app.errorhandler(SessionClosed)
    def _closed(e):
        return fail(409, "session_closed", "This session has already ended.", e.args[0] if e.args else None)

    @app.errorhandler(SessionExpired)
    def _expired(e):
        return fail(410, "session_expired", "The session time is over.", e.args[0] if e.args else None)

    @app.errorhandler(SessionActive)
    def _active(e):
        return fail(409, "session_active", "The session is still running.")

    @app.errorhandler(Exception)
    def _any(e):
        if isinstance(e, HTTPException):
            return fail(e.code, e.name.lower().replace(" ", "_"), e.description)
        app.logger.exception("Unhandled error")
        return fail(500, "internal_error", "Something went wrong. Please try again.")

    @app.after_request
    def _headers(resp):
        if request.path.startswith("/api/") or request.path == "/health":
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ---- Health ----
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # ---- API ----
    @app.post("/api/session/start")
    def start():
        r = orch.start_session()
        return jsonify({
            "session_id": r["session_id"],
            "duration": r["duration"],
            "opening": r["opening"],
            "suggestions": r["suggestions"],
        })

    @app.post("/api/chat")
    def chat():
        d = body()
        sid = validate_session_id(d.get("session_id"))
        return jsonify(orch.handle_message(sid, validate_message(d.get("message"), cfg["MAX_MESSAGE_CHARS"])))

    @app.post("/api/session/end")
    def end():
        sid = validate_session_id(body().get("session_id"))
        return jsonify({"session_id": sid, "report": orch.end_session(sid)})

    @app.get("/api/session/<sid>/report")
    def report(sid):
        return jsonify(orch.get_report(validate_session_id(sid)))

    @app.get("/api/session/<sid>")
    def state(sid):
        return jsonify(orch.state(validate_session_id(sid)))

    @app.delete("/api/session/<sid>")
    def delete(sid):
        if not orch.sessions.delete(validate_session_id(sid)):
            raise SessionNotFound(sid)
        return jsonify({"deleted": True})

    return app


if __name__ == "__main__":
    # Local API server only. Frontend is served separately (e.g. python -m http.server 5500).
    create_app().run(host="127.0.0.1", port=Config.PORT, debug=False)
