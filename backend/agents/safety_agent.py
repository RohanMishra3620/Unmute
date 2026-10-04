from backend.services.regex_engine import RISK_LEVELS, max_risk
import re

HIGH = ("HIGH_CONCERN", "CRISIS")
CRISIS_TEXT = ("I'm really concerned about your safety right now. Please contact your local emergency service or go to the "
               "nearest emergency department, and try to be with someone you trust. Are you in immediate danger?")
HIGH_TEXT = ("I'm sorry you're in this much pain, and I'm glad you told me. Please reach out to a crisis line, an emergency "
             "service or someone you trust right now. Are you safe at this moment?")
OTHERS_TEXT = ("It sounds like things feel very intense. Please step away from the situation, and contact emergency services "
               "if anyone could be in danger. Are you and others safe right now?")
UNSAFE = re.compile(r"\b(not|n't) (safe|ok|okay)\b|\bunsafe\b|\bin danger\b|\bno\b")
SAFE_NOW = re.compile(r"\b(yes|yeah|i am|i'?m)\b.{0,15}\b(safe|ok|okay|fine)\b|\bnot in (immediate )?danger\b")


class SafetyAgent:
    """Highest-priority agent. Its verdict can never be overridden by the conversation agent."""

    def __init__(self, cfg):
        self.cfg = cfg

    def assess(self, rx, prior_level="SAFE", llm_level=None):
        level = rx["risk_level"]
        if llm_level in RISK_LEVELS:
            level = max_risk(level, llm_level)  # LLM may escalate, never lower
        crisis = level in HIGH
        return {"level": level, "is_crisis": crisis, "followup": (not crisis) and prior_level in HIGH}

    def crisis_reply(self, verdict, rx):
        cats = set(rx["categories"])
        if verdict["level"] == "CRISIS" or "immediate_danger" in cats:
            return CRISIS_TEXT
        if "harm_others" in cats and not cats & {"suicide", "self_harm"}:
            return OTHERS_TEXT
        return HIGH_TEXT

    def followup_reply(self, text):
        t = text.lower().replace("\u2019", "'")
        if UNSAFE.search(t):
            return ("Thank you for telling me. Please contact emergency services or go to the nearest emergency department now, "
                    "and tell someone near you. Can you reach someone right now?")
        if SAFE_NOW.search(t):
            return ("I'm glad you feel safe right now. Please talk to someone you trust or a crisis line today. "
                    "Would you like to tell me a bit more about what has been happening?")
        return ("Thank you for staying with me. Please reach out to emergency services or someone you trust if things feel unsafe. "
                "Are you safe right now?")
