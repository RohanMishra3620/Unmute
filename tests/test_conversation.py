from backend.services.regex_engine import analyze
from tests.test_api import say, sentences, start


def test_new_signals_for_case_and_fear():
    cats = analyze("I am afraid of them, the court hearing is close and the memories keep coming back")["categories"]
    assert {"case_stress", "fear", "trauma_memory"} <= set(cats)


def test_replies_never_repeat_in_a_session(client):
    sid = start(client)
    replies = [say(client, sid, m).json["reply"] for m in
               ["I feel stressed", "I feel stressed", "I feel stressed", "still stressed", "stressed again", "very stressed"]]
    assert len(set(replies)) == len(replies)
    seen = set()
    for r in replies:                       # no single sentence is said twice either
        for s in sentences(r):
            assert s not in seen
            seen.add(s)


def test_fear_gets_a_safety_question_first(client):
    r = say(client, start(client), "I am afraid of them, they will find me")
    assert "safe" in r.json["reply"].lower() and r.json["suggestions"]


def test_short_answers_get_gentle_help(client):
    sid = start(client)
    say(client, sid, "I feel sad")
    r = say(client, sid, "ok")
    assert r.status_code == 200 and "My mind" in r.json["suggestions"]


def test_closing_reply_near_the_end(client, clock):
    sid = start(client)
    clock.advance(270)
    r = say(client, sid, "I feel anxious about everything")
    assert r.status_code == 200 and "take care" in r.json["reply"].lower() or "trust" in r.json["reply"].lower()


