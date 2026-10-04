import re


def start(client):
    r = client.post("/api/session/start")
    assert r.status_code == 200 and r.json["duration"] == 300
    return r.json["session_id"]


def say(client, sid, msg):
    return client.post("/api/chat", json={"session_id": sid, "message": msg})


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t) if s]


def test_index_is_branded(client):
    r = client.get("/")
    assert r.status_code == 200 and b"Unmute" in r.data and b"MindCare" not in r.data


def test_normal_conversation(client):
    r = say(client, start(client), "hello")
    assert r.status_code == 200 and r.json["risk_level"] == "SAFE" and r.json["reply"]
    assert 0 < r.json["remaining_seconds"] <= 300


def test_stress_anxiety_sleep_messages(client):
    sid = start(client)
    for msg in ["I have been feeling very stressed lately", "I feel anxious and can't stop overthinking", "I can't sleep at night"]:
        r = say(client, sid, msg)
        assert r.json["risk_level"] == "LOW_CONCERN"
        assert len(sentences(r.json["reply"])) <= 3


def test_high_risk_message_gets_crisis_response(client):
    r = say(client, start(client), "I want to kill myself")
    assert r.json["risk_level"] in ("HIGH_CONCERN", "CRISIS")
    assert "emergency" in r.json["reply"].lower() and r.json["emergency"]["message"]


def test_session_expiration(client, clock):
    sid = start(client)
    clock.advance(301)
    r = say(client, sid, "are you there")
    assert r.status_code == 410 and r.json["report_url"].endswith(sid)
    assert client.get(f"/api/session/{sid}/report").status_code == 200
    assert say(client, sid, "hello").status_code == 409


def test_report_generation(client):
    sid = start(client)
    say(client, sid, "I'm so stressed about my exams and I can't sleep")
    assert client.get(f"/api/session/{sid}/report").status_code == 409  # still running
    r = client.post("/api/session/end", json={"session_id": sid})
    assert r.status_code == 200
    rep = client.get(f"/api/session/{sid}/report").json
    assert "stress" in rep["dominant_emotions"] and "academic pressure" in rep["main_topics"]
    assert rep["risk_level"] == "LOW_CONCERN" and "not a medical diagnosis" in rep["disclaimer"]
    assert "disorder" not in rep["summary"].lower()
    assert client.get(f"/report/{sid}").status_code == 200


def test_invalid_session_id(client):
    assert say(client, "nope", "hi").status_code == 400
    assert say(client, "a" * 32, "hi").status_code == 404
    assert client.get("/api/session/" + "b" * 32 + "/report").status_code == 404
    assert client.post("/api/chat", data="not json").status_code == 400


def test_empty_message(client):
    sid = start(client)
    assert say(client, sid, "").status_code == 400
    assert say(client, sid, "   ").status_code == 400
    assert say(client, sid, "x" * 1001).status_code == 400


def test_delete_session(client):
    sid = start(client)
    say(client, sid, "I feel sad")
    assert client.delete(f"/api/session/{sid}").status_code == 200
    assert client.get(f"/api/session/{sid}").status_code == 404
    assert say(client, sid, "hi").status_code == 404
    assert client.delete(f"/api/session/{sid}").status_code == 404
