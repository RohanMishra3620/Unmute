from agents.safety_agent import SafetyAgent
from config import Config
from services.regex_engine import analyze

agent = SafetyAgent(Config.as_dict())


def test_safe_message():
    v = agent.assess(analyze("hello"), "SAFE")
    assert not v["is_crisis"] and not v["followup"]


def test_high_risk_is_crisis_with_direct_reply():
    rx = analyze("I'm going to kill myself tonight")
    v = agent.assess(rx, "SAFE")
    assert v["is_crisis"] and v["level"] == "CRISIS"
    reply = agent.crisis_reply(v, rx)
    assert "emergency" in reply.lower() and reply.endswith("?")


def test_llm_can_escalate_but_never_lower():
    assert agent.assess(analyze("hello"), "SAFE", "HIGH_CONCERN")["is_crisis"]
    assert agent.assess(analyze("I want to kill myself"), "SAFE", "SAFE")["level"] == "HIGH_CONCERN"


def test_followup_after_crisis():
    assert agent.assess(analyze("yes I am safe"), "HIGH_CONCERN")["followup"]
    assert "glad" in agent.followup_reply("yes I am safe").lower()
    assert "emergency" in agent.followup_reply("no I am not safe").lower()
