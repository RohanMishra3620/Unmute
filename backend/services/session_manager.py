import json
import math
import time
import uuid

from backend.services.regex_engine import max_risk


class SessionError(Exception):
    pass


class SessionNotFound(SessionError):
    pass


class SessionClosed(SessionError):
    pass


class SessionExpired(SessionError):
    pass


class SessionActive(SessionError):
    pass


class SessionManager:
    """Owns session state. The server clock is the source of truth for the timer."""

    def __init__(self, db, duration, clock=time.time):
        self.db, self.duration, self.clock = db, duration, clock

    def _one(self, sql, args=()):
        with self.db.conn() as c:
            r = c.execute(sql, args).fetchone()
        return dict(r) if r else None

    def _all(self, sql, args=()):
        with self.db.conn() as c:
            return [dict(r) for r in c.execute(sql, args).fetchall()]

    def _run(self, sql, args=()):
        with self.db.conn() as c:
            cur = c.execute(sql, args)
            return cur.lastrowid, cur.rowcount

    def start(self):
        sid = uuid.uuid4().hex
        self._run("INSERT INTO sessions(session_id, started_at) VALUES (?, ?)", (sid, self.clock()))
        return self.get(sid)

    def get(self, sid):
        return self._one("SELECT * FROM sessions WHERE session_id=?", (sid,))

    def require(self, sid):
        s = self.get(sid)
        if not s:
            raise SessionNotFound(sid)
        return s

    def remaining(self, s):
        return max(0, math.ceil(s["started_at"] + self.duration - self.clock()))

    def add_message(self, sid, role, text):
        return self._run("INSERT INTO messages(session_id, role, message, timestamp) VALUES (?,?,?,?)",
                         (sid, role, text, self.clock()))[0]

    def messages(self, sid):
        return self._all("SELECT id, role, message, timestamp FROM messages WHERE session_id=? ORDER BY id", (sid,))

    def add_analysis(self, sid, mid, a, risk):
        self._run("INSERT INTO analyses(session_id, message_id, emotion, intensity, risk_level, signals) VALUES (?,?,?,?,?,?)",
                  (sid, mid, a["emotion"], a["intensity"], risk, json.dumps(a["signals"])))

    def analyses(self, sid):
        rows = self._all("SELECT emotion, intensity, risk_level, signals FROM analyses WHERE session_id=? ORDER BY id", (sid,))
        for r in rows:
            r["signals"] = json.loads(r["signals"] or "[]")
        return rows

    def last_risk(self, sid):
        r = self._one("SELECT risk_level FROM analyses WHERE session_id=? ORDER BY id DESC LIMIT 1", (sid,))
        return r["risk_level"] if r else "SAFE"

    def raise_risk(self, sid, level):
        s = self.require(sid)
        self._run("UPDATE sessions SET risk_level=? WHERE session_id=?", (max_risk(s["risk_level"], level), sid))

    def close(self, sid, status):
        s = self.require(sid)
        if s["status"] != "active":
            return s
        end = min(self.clock(), s["started_at"] + self.duration)
        self._run("UPDATE sessions SET status=?, ended_at=?, duration=? WHERE session_id=?",
                  (status, end, int(round(end - s["started_at"])), sid))
        return self.get(sid)

    def save_report(self, sid, r):
        self._run(
            """INSERT INTO reports(session_id, summary, dominant_emotions, main_topics, risk_level, recommendations, created_at, data)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET summary=excluded.summary, dominant_emotions=excluded.dominant_emotions,
               main_topics=excluded.main_topics, risk_level=excluded.risk_level, recommendations=excluded.recommendations,
               created_at=excluded.created_at, data=excluded.data""",
            (sid, r["summary"], json.dumps(r["dominant_emotions"]), json.dumps(r["main_topics"]), r["risk_level"],
             json.dumps(r["suggested_next_steps"]), self.clock(), json.dumps(r)))

    def get_report(self, sid):
        row = self._one("SELECT data FROM reports WHERE session_id=?", (sid,))
        return json.loads(row["data"]) if row else None

    def delete(self, sid):
        return self._run("DELETE FROM sessions WHERE session_id=?", (sid,))[1] > 0
