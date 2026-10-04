from backend.models.database import Database
from backend.services.session_manager import SessionManager, SessionNotFound
import pytest
from tests.conftest import FakeClock


def make(tmp_path):
    clock = FakeClock()
    return SessionManager(Database(str(tmp_path / "s.db")), 300, clock), clock


def test_timer_is_server_side(tmp_path):
    sm, clock = make(tmp_path)
    s = sm.start()
    assert sm.remaining(s) == 300
    clock.advance(100)
    assert sm.remaining(s) == 200
    clock.advance(500)
    assert sm.remaining(s) == 0


def test_close_is_idempotent_and_caps_duration(tmp_path):
    sm, clock = make(tmp_path)
    sid = sm.start()["session_id"]
    clock.advance(1000)
    assert sm.close(sid, "expired")["duration"] == 300
    assert sm.close(sid, "ended")["status"] == "expired"


def test_messages_and_delete_cascade(tmp_path):
    sm, _ = make(tmp_path)
    sid = sm.start()["session_id"]
    sm.add_message(sid, "user", "hi")
    assert len(sm.messages(sid)) == 1
    assert sm.delete(sid) and sm.get(sid) is None and sm.messages(sid) == []
    with pytest.raises(SessionNotFound):
        sm.require(sid)
