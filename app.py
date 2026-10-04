from flask import Flask, jsonify, redirect, render_template, request
from werkzeug.exceptions import HTTPException

from config import Config
from models.schemas import ValidationError, validate_message, validate_session_id
from services.orchestrator import Orchestrator
from services.session_manager import SessionActive, SessionClosed, SessionExpired, SessionNotFound


def create_app(overrides=None):
    cfg = Config.as_dict()
    cfg.update(overrides or {})
    app = Flask(__name__)
    app.config.update(cfg)
    app.orchestrator = orch = Orchestrator(cfg)

    @app.context_processor
    def inject():
        return {"app_name": cfg["APP_NAME"], "minutes": cfg["SESSION_SECONDS"] // 60, "total_seconds": cfg["SESSION_SECONDS"],
                "emergency_message": cfg["EMERGENCY_MESSAGE"], "contacts": cfg["EMERGENCY_CONTACTS"]}

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")
        return data

    def fail(code, key, msg, sid=None):
        out = {"error": key, "message": msg}
        if sid:
            out["report_url"] = f"/report/{sid}"
        return jsonify(out), code

    @app.errorhandler(ValidationError)
    def _invalid(e):
        return fail(400, "invalid_request", str(e))

    @app.errorhandler(SessionNotFound)
    def _missing(e):
        return fail(404, "session_not_found", "Session not found.")

    @app.errorhandler(SessionClosed)
    def _closed(e):
        return fail(409, "session_closed", "This session has already ended.", e.args[0])

    @app.errorhandler(SessionExpired)
    def _expired(e):
        return fail(410, "session_expired", "The session time is over.", e.args[0])

    @app.errorhandler(SessionActive)
    def _active(e):
        return fail(409, "session_active", "The session is still running.")

    @app.errorhandler(Exception)
    def _any(e):
        if isinstance(e, HTTPException):
            return fail(e.code, e.name.lower().replace(" ", "_"), e.description) if request.path.startswith("/api/") else e
        app.logger.exception("Unhandled error")
        return fail(500, "internal_error", "Something went wrong. Please try again.")

    @app.after_request
    def _headers(resp):
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ---- API ----
    @app.post("/api/session/start")
    def start():
        r = orch.start_session()
        return jsonify({"session_id": r["session_id"], "duration": r["duration"], "opening": r["opening"],
                        "suggestions": r["suggestions"]})

    @app.post("/api/chat")
    def chat():
        d = body()
        sid = validate_session_id(d.get("session_id"))
        return jsonify(orch.handle_message(sid, validate_message(d.get("message"), cfg["MAX_MESSAGE_CHARS"])))

    @app.post("/api/session/end")
    def end():
        sid = validate_session_id(body().get("session_id"))
        return jsonify({"session_id": sid, "report": orch.end_session(sid), "report_url": f"/report/{sid}"})

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

    # ---- Pages ----
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/chat/<sid>")
    def chat_page(sid):
        try:
            s = orch.sessions.require(validate_session_id(sid))
        except (ValidationError, SessionNotFound):
            return render_template("index.html", notice="That session was not found."), 404
        if s["status"] != "active":
            return redirect(f"/report/{sid}")
        return render_template("chat.html", sid=sid)

    @app.get("/report/<sid>")
    def report_page(sid):
        try:
            r = orch.get_report(validate_session_id(sid))
        except SessionActive:
            return redirect(f"/chat/{sid}")
        except (ValidationError, SessionNotFound):
            return render_template("index.html", notice="That session was not found or was deleted."), 404
        return render_template("report.html", r=r, sid=sid)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=Config.PORT, debug=False)
