import os

from agents.analysis_agent import AnalysisAgent
from agents.conversation_agent import ConversationAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.report_agent import ReportAgent
from agents.safety_agent import HIGH, SafetyAgent
from models.database import Database
from services import regex_engine
from services.llm_service import LLMService
from services.regex_engine import max_risk
from services.session_manager import SessionActive, SessionClosed, SessionExpired, SessionManager

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base", "mental_health.json")
OPENING = ("Namaste, I am Unmute, an AI support tool (not a doctor or therapist). This is a safe space, there are no right or wrong "
           "answers, and you can take your time. To begin, how are you feeling today?")
OPEN_CHIPS = ["I am feeling stressed", "I am worried about my case", "I cannot sleep properly", "I feel scared or alone", "I am doing okay today"]
SAFE_CHIPS = ["Yes, I am safe", "No, I am not safe"]


class Orchestrator:
    """Regex -> Safety -> Analysis -> Knowledge -> Conversation. Safety always wins."""

    def __init__(self, cfg, llm=None):
        self.cfg = cfg
        self.sessions = SessionManager(Database(cfg["DB_PATH"]), cfg["SESSION_SECONDS"])
        self.llm = llm or LLMService(cfg)
        self.safety = SafetyAgent(cfg)
        self.analysis = AnalysisAgent(self.llm)
        self.kb = KnowledgeAgent(KB_PATH)
        self.conversation = ConversationAgent(self.llm)
        self.reports = ReportAgent(self.llm, self.kb, cfg)

    def emergency(self):
        return {"message": self.cfg["EMERGENCY_MESSAGE"], "contacts": self.cfg["EMERGENCY_CONTACTS"]}

    def start_session(self):
        s = self.sessions.start()
        self.sessions.add_message(s["session_id"], "assistant", OPENING)
        return {"session_id": s["session_id"], "duration": self.cfg["SESSION_SECONDS"], "opening": OPENING, "suggestions": OPEN_CHIPS}

    def state(self, sid):
        s = self.sessions.require(sid)
        if s["status"] == "active" and self.sessions.remaining(s) <= 0:
            self._finish(sid, "expired")
            s = self.sessions.get(sid)
        active = s["status"] == "active"
        return {"session_id": sid, "status": s["status"], "remaining_seconds": self.sessions.remaining(s) if active else 0,
                "risk_level": s["risk_level"], "emergency": self.emergency() if s["risk_level"] in HIGH else None,
                "messages": [{"role": m["role"], "message": m["message"]} for m in self.sessions.messages(sid)]}

    def handle_message(self, sid, text):
        s = self.sessions.require(sid)
        if s["status"] != "active":
            raise SessionClosed(sid)
        if self.sessions.remaining(s) <= 0:
            self._finish(sid, "expired")
            raise SessionExpired(sid)
        history = self.sessions.messages(sid)
        turn = sum(1 for m in history if m["role"] == "user")
        prior = self.sessions.last_risk(sid)

        rx = regex_engine.analyze(text)                       # 1. deterministic layer
        verdict = self.safety.assess(rx, prior)               # 2. safety agent
        mid = self.sessions.add_message(sid, "user", text)
        analysis = self.analysis.analyze(text, rx, history, use_llm=not verdict["is_crisis"])  # 3. analysis agent
        if not verdict["is_crisis"]:
            verdict = self.safety.assess(rx, prior, analysis.get("risk_hint"))  # contextual re-check, may escalate

        chips = []
        if verdict["is_crisis"]:
            reply, chips = self.safety.crisis_reply(verdict, rx), SAFE_CHIPS
        elif verdict["followup"]:
            reply, chips = self.safety.followup_reply(text), SAFE_CHIPS
        else:
            sigs = list(analysis["signals"])
            if not sigs:                                       # short replies like "ok": reuse what the session was about
                for a in reversed(self.sessions.analyses(sid)):
                    sigs = [x for x in a["signals"] if x not in ("positive", "help_seeking", "coping_used")]
                    if sigs:
                        break
            entries = self.kb.retrieve(sigs)                   # 4. knowledge agent
            out = self.conversation.respond_full(text, history, analysis, entries, turn,   # 5. conversation agent
                                                 self.sessions.remaining(s), s["risk_level"])
            reply, chips = out["reply"], out["suggestions"]
        level = verdict["level"]
        self.sessions.add_analysis(sid, mid, analysis, level)
        self.sessions.raise_risk(sid, level)
        self.sessions.add_message(sid, "assistant", reply)
        return {"reply": reply, "risk_level": level, "remaining_seconds": self.sessions.remaining(self.sessions.require(sid)),
                "emergency": self.emergency() if level in HIGH else None, "suggestions": chips}

    def _finish(self, sid, status):
        self.sessions.close(sid, status)
        report = self.reports.generate(self.sessions.require(sid), self.sessions.messages(sid), self.sessions.analyses(sid))
        self.sessions.save_report(sid, report)
        return report

    def end_session(self, sid):
        s = self.sessions.require(sid)
        if s["status"] == "active":
            self._finish(sid, "expired" if self.sessions.remaining(s) <= 0 else "ended")
        return self.get_report(sid)

    def get_report(self, sid):
        s = self.sessions.require(sid)
        if s["status"] == "active":
            if self.sessions.remaining(s) > 0:
                raise SessionActive(sid)
            self._finish(sid, "expired")
        report = self.sessions.get_report(sid) or self._finish(sid, s["status"])
        report["emergency"] = self.emergency() if report["risk_level"] in HIGH else None
        return report
